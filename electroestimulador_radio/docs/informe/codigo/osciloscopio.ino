/*
  OSCILOSCOPIO ARDUINO - firmware
  Placas: Arduino Uno / Nano / Duemilanove (ATmega328P o ATmega168)

  Se usa junto con osciloscopio.html (abrir en Chrome o Edge y pulsar "Conectar").

  Entradas:  A0..A5 (A6 y A7 en el Nano). Solo 0 a 5 V. Nunca voltajes negativos
             ni mayores a 5 V directo al pin: usar un divisor resistivo.
  Salida:    D3 = generador de senal de prueba (solo si se activa desde la app).

  Como funciona:
    - El Timer1 marca el instante de cada muestra; el codigo solo espera su
      bandera y arranca la conversion, asi que el tiempo entre muestras es
      exacto (variacion menor a 1 microsegundo). No se usa el disparo
      automatico del ADC porque varios chips clonicos no lo implementan.
    - Modo rafaga: llena un buffer circular en RAM (con disparo y pre-disparo)
      y despues lo envia. Hasta 100 000 muestras por segundo.
    - Modo continuo (roll): envia las muestras a medida que se toman, para
      senales lentas.
    - La PC calcula todos los registros y los manda en cada peticion; el
      firmware no guarda configuracion.
    - No se usa ninguna interrupcion ni la clase Serial: todo es por sondeo,
      para que nada altere el muestreo.

  Protocolo (500000 baudios, 8N1):
    PC -> Arduino: 20 bytes  [0xA5, cmd, 17 parametros, xor de los 19 anteriores]
                   Un byte 0x00 suelto cancela la captura en curso.
    Arduino -> PC: [0xA5, 0x5A, tipo, largoL, largoH, datos..., xor de los datos]
*/

#include <avr/io.h>
#include <util/delay.h>

#define FW_VERSION 1
#define BAUDIOS    500000UL
#define CMD_LEN    20

#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega328__)
  #define BUF_SIZE 1800
#elif defined(__AVR_ATmega168__) || defined(__AVR_ATmega168P__)
  #define BUF_SIZE 800
#else
  #error "Este firmware es para ATmega328P / ATmega168 (Uno, Nano, Duemilanove)"
#endif

static uint8_t buf[BUF_SIZE];
static uint8_t cmd[CMD_LEN];
static uint8_t ultimaRef = 0xFF;

// ---------------------------------------------------------------- UART
static inline void tx(uint8_t b) {
  while (!(UCSR0A & _BV(UDRE0))) {}
  UDR0 = b;
}

static inline uint8_t hayRx() {
  return UCSR0A & _BV(RXC0);
}

static void cabecera(uint8_t tipo, uint16_t largo) {
  tx(0xA5);
  tx(0x5A);
  tx(tipo);
  tx(largo & 0xFF);
  tx(largo >> 8);
}

static void tramaCorta(uint8_t tipo, const uint8_t *datos, uint8_t largo) {
  uint8_t x = 0;
  cabecera(tipo, largo);
  for (uint8_t i = 0; i < largo; i++) {
    tx(datos[i]);
    x ^= datos[i];
  }
  tx(x);
}

static void enviarError(uint8_t codigo) {
  tramaCorta('E', &codigo, 1);
}

// ---------------------------------------------------------------- ADC + Timer1
// Deja el ADC y el Timer1 listos. El timer queda detenido y con su bandera limpia.
// Devuelve el valor de ADCSRA que arranca una conversion.
static uint8_t prepararAdc(uint8_t refBits, uint8_t mux, uint8_t adps, uint16_t ocr) {
  TCCR1B = 0;                         // timer detenido
  TCCR1A = 0;
  TIMSK1 = 0;

  ADCSRB = 0;
  ADMUX = refBits | _BV(ADLAR) | mux;
  ADCSRA = _BV(ADEN) | adps;

  if (refBits != ultimaRef) {         // al cambiar de referencia hay que esperar al capacitor de AREF
    _delay_ms(60);
    ultimaRef = refBits;
  }
  uint8_t arrancar = _BV(ADEN) | _BV(ADSC) | _BV(ADIF) | adps;
  for (uint8_t i = 0; i < 2; i++) {   // conversiones de descarte (la primera tarda mas)
    ADCSRA = arrancar;
    while (ADCSRA & _BV(ADSC)) {}
  }

  TCNT1 = 0;
  OCR1A = ocr;                        // TOP (modo CTC): un "tic" por muestra
  TIFR1 = _BV(OCF1A);
  return arrancar;
}

static inline void arrancarTimer(uint8_t cs) {
  TCCR1B = _BV(WGM12) | cs;
}

static inline void detenerTimer() {
  TCCR1B = 0;
  ADCSRA = _BV(ADEN) | 7;
}

// ---------------------------------------------------------------- Rafaga
/*
  Parametros (cmd[2..]):
    [2]  flags: b0 dos canales, b1 10 bits, b2 disparo activo, b3 flanco de bajada,
                b4 canal de disparo (0 = A, 1 = B), b5 referencia interna 1.1 V
    [3]  pin canal A (0..7)        [4]  pin canal B (0..7)
    [5]  prescaler ADC (ADPS 1..7) [6]  prescaler Timer1 (CS 1..5)
    [7,8]   OCR1A
    [9,10]  n    = conversiones a guardar (par si hay dos canales)
    [11,12] post = conversiones despues del disparo
    [13] nivel de disparo (8 bits) [14] histeresis
    [15,16] espera maxima en conversiones (0 = esperar para siempre)
*/
enum { E_PRELLENADO, E_ARMAR, E_ESPERAR, E_POST };

static void rafaga() {
  uint8_t flags   = cmd[2];
  uint8_t dual    = flags & 0x01;
  uint8_t hires   = flags & 0x02;
  uint8_t trigOn  = flags & 0x04;
  uint8_t bajada  = flags & 0x08;
  uint8_t trigCh  = dual ? ((flags >> 4) & 1) : 0;
  uint8_t refBits = (flags & 0x20) ? (_BV(REFS1) | _BV(REFS0)) : _BV(REFS0);
  uint8_t adps    = cmd[5] & 7;
  uint8_t cs      = cmd[6] & 7;
  uint16_t ocr    = cmd[7]  | ((uint16_t)cmd[8]  << 8);
  uint16_t n      = cmd[9]  | ((uint16_t)cmd[10] << 8);
  uint16_t post   = cmd[11] | ((uint16_t)cmd[12] << 8);
  uint8_t nivel   = cmd[13];
  uint8_t hist    = cmd[14];
  uint16_t espera = cmd[15] | ((uint16_t)cmd[16] << 8);

  uint16_t bytes = hires ? n * 2 : n;
  if (n < 2 || n > BUF_SIZE || bytes > BUF_SIZE || (dual && (n & 1)) ||
      cs < 1 || cs > 5 || adps < 1 || (trigOn && (post < 1 || post >= n))) {
    enviarError(2);
    return;
  }

  uint8_t muxA = refBits | _BV(ADLAR) | (cmd[3] & 7);
  uint8_t muxB = refBits | _BV(ADLAR) | (cmd[4] & 7);

  uint8_t inv = bajada ? 0xFF : 0x00;
  uint8_t lvl = bajada ? (uint8_t)(255 - nivel) : nivel;
  uint8_t bajo = (lvl > hist) ? (uint8_t)(lvl - hist) : (lvl ? 1 : 0);

  uint8_t *p = buf;
  uint8_t *fin = buf + bytes;
  uint8_t estado;
  uint16_t cuenta;
  if (trigOn) {
    estado = E_PRELLENADO;
    cuenta = n - post;
  } else {
    estado = E_POST;
    cuenta = n;
  }
  uint8_t ch = 0;                     // canal de la conversion en curso
  uint8_t cebado = 0;
  uint8_t cancelado = 0;
  uint8_t automatico = 0;

  uint8_t arrancar = prepararAdc(refBits, cmd[3] & 7, adps, ocr);
  arrancarTimer(cs);

  // En cada tic: se lee la conversion anterior (ya terminada), se arranca la
  // siguiente y, mientras esa convierte, se procesa la muestra leida.
  for (;;) {
    while (!(TIFR1 & _BV(OCF1A))) {
      if (UCSR0A & _BV(RXC0)) {
        cancelado = 1;
        break;
      }
    }
    if (cancelado) break;

    TIFR1 = _BV(OCF1A);
    uint8_t lo = ADCL;
    uint8_t v = ADCH;
    uint8_t sch = ch;                 // canal de la muestra recien leida
    if (cebado && dual) {
      ch ^= 1;
      ADMUX = ch ? muxB : muxA;
    }
    ADCSRA = arrancar;
    if (!cebado) {                    // en el primer tic todavia no hay muestra valida
      cebado = 1;
      continue;
    }

    *p++ = v;
    if (hires) *p++ = lo;
    if (p == fin) p = buf;

    if (estado == E_POST) {
      if (--cuenta == 0) break;
      continue;
    }
    if (estado == E_PRELLENADO) {
      if (--cuenta == 0) estado = E_ARMAR;
      continue;
    }
    if (sch == trigCh) {
      v ^= inv;
      if (estado == E_ARMAR) {
        if (v < bajo) estado = E_ESPERAR;
      } else if (v >= lvl) {
        estado = E_POST;
        cuenta = post;
        continue;
      }
    }
    if (espera && --espera == 0) {
      estado = E_POST;
      cuenta = post;
      automatico = 1;
    }
  }
  detenerTimer();

  if (cancelado) {
    (void)UDR0;                       // descartar el byte de cancelacion
    tramaCorta('A', 0, 0);
    return;
  }

  // Enviar en orden cronologico: de p hasta el final y luego del inicio hasta p
  uint16_t inicio = p - buf;
  uint8_t primerCanal = dual ? ((hires ? (inicio >> 1) : inicio) & 1) : 0;
  uint8_t f = (automatico ? 0x01 : 0) | (primerCanal ? 0x02 : 0) | (hires ? 0x04 : 0) | (dual ? 0x08 : 0);
  uint8_t x = f;
  cabecera('B', bytes + 1);
  tx(f);
  for (uint8_t *q = p; q != fin; q++) {
    tx(*q);
    x ^= *q;
  }
  for (uint8_t *q = buf; q != p; q++) {
    tx(*q);
    x ^= *q;
  }
  tx(x);
}

// ---------------------------------------------------------------- Continuo (roll)
/*
  Parametros: [2] flags (b0 dos canales, b5 ref 1.1 V), [3] pin A, [4] pin B,
              [5] ADPS, [6] CS, [7,8] OCR1A, [9] conversiones por trama (par si dual)
  Siempre 10 bits: cada muestra son 2 bytes (ADCH, ADCL).
  Se detiene al recibir cualquier byte (se revisa al final de cada trama).
*/
static void continuo() {
  uint8_t flags   = cmd[2];
  uint8_t dual    = flags & 0x01;
  uint8_t refBits = (flags & 0x20) ? (_BV(REFS1) | _BV(REFS0)) : _BV(REFS0);
  uint8_t adps    = cmd[5] & 7;
  uint8_t cs      = cmd[6] & 7;
  uint16_t ocr    = cmd[7] | ((uint16_t)cmd[8] << 8);
  uint8_t porTrama = cmd[9];

  if (porTrama < 1 || (dual && (porTrama & 1)) || cs < 1 || cs > 5 || adps < 1) {
    enviarError(3);
    return;
  }

  uint8_t muxA = refBits | _BV(ADLAR) | (cmd[3] & 7);
  uint8_t muxB = refBits | _BV(ADLAR) | (cmd[4] & 7);
  uint8_t ch = 0;
  uint8_t seq = 0;

  uint8_t arrancar = prepararAdc(refBits, cmd[3] & 7, adps, ocr);
  arrancarTimer(cs);

  while (!(TIFR1 & _BV(OCF1A))) {}    // primer tic: arranca la primera conversion (canal A)
  TIFR1 = _BV(OCF1A);
  ADCSRA = arrancar;

  for (;;) {
    cabecera('S', (uint16_t)porTrama * 2 + 1);
    tx(seq);
    uint8_t x = seq;
    for (uint8_t i = 0; i < porTrama; i++) {
      while (!(TIFR1 & _BV(OCF1A))) {}
      TIFR1 = _BV(OCF1A);
      uint8_t lo = ADCL;
      uint8_t hi = ADCH;
      if (dual) {
        ch ^= 1;
        ADMUX = ch ? muxB : muxA;
      }
      ADCSRA = arrancar;
      tx(hi);
      tx(lo);
      x ^= hi ^ lo;
    }
    tx(x);
    seq++;
    if (hayRx()) break;
  }
  detenerTimer();
  (void)UDR0;
  tramaCorta('A', 0, 0);
}

// ---------------------------------------------------------------- Generador (D3, Timer2)
// Parametros: [2] activar, [3] TCCR2A, [4] TCCR2B, [5] OCR2A, [6] OCR2B
static void generador() {
  TCCR2B = 0;
  TCCR2A = 0;
  if (cmd[2]) {
    TCNT2 = 0;
    OCR2A = cmd[5];
    OCR2B = cmd[6];
    DDRD |= _BV(PD3);
    TCCR2A = cmd[3];
    TCCR2B = cmd[4];
  } else {
    DDRD &= ~_BV(PD3);
    PORTD &= ~_BV(PD3);
  }
  tramaCorta('G', 0, 0);
}

static void identificar() {
  uint8_t d[4] = { FW_VERSION, (uint8_t)(F_CPU / 1000000UL), (uint8_t)(BUF_SIZE & 0xFF), (uint8_t)(BUF_SIZE >> 8) };
  tramaCorta('I', d, 4);
}

// ---------------------------------------------------------------- Principal
void setup() {
  TIMSK0 = 0;                         // sin interrupciones: millis()/delay() de Arduino no se usan

  UCSR0A = _BV(U2X0);
  UBRR0 = (F_CPU / (8UL * BAUDIOS)) - 1;
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
  UCSR0B = _BV(RXEN0) | _BV(TXEN0);

  DIDR0 = 0x3F;                       // apagar los buffers digitales de A0..A5 (menos ruido)
  ADCSRA = _BV(ADEN) | 7;
}

void loop() {
  if (!hayRx()) return;
  if (UDR0 != 0xA5) return;           // buscar inicio de comando
  cmd[0] = 0xA5;

  uint8_t x = 0xA5;
  for (uint8_t i = 1; i < CMD_LEN; i++) {
    uint16_t t = 0;
    while (!hayRx()) {
      if (++t == 0) return;           // comando incompleto: descartar
    }
    cmd[i] = UDR0;
    if (i < CMD_LEN - 1) x ^= cmd[i];
  }
  if (x != cmd[CMD_LEN - 1]) {
    enviarError(1);
    return;
  }

  switch (cmd[1]) {
    case 'I': identificar(); break;
    case 'B': rafaga();      break;
    case 'S': continuo();    break;
    case 'G': generador();   break;
    default:  enviarError(4); break;
  }
}
