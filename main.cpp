#include "mbed.h"

/////////////////////
// Pin definitions //
/////////////////////

//Photointerrupter input pins
#define I1pin D2
#define I2pin D11
#define I3pin D12

DigitalIn I1(I1pin);
DigitalIn I2(I2pin);
DigitalIn I3(I3pin);

InterruptIn I1intr(I1pin);
InterruptIn I2intr(I2pin);
InterruptIn I3intr(I3pin);

//Incremental encoder input pins
#define CHA   D7
#define CHB   D8  

DigitalIn CHAR(CHA);
DigitalIn CHBR(CHB);

InterruptIn CHAintr(CHA);
InterruptIn CHBintr(CHB);

//Status LED
DigitalOut led1 (LED1);
DigitalOut led2 (LED2);
DigitalOut led3 (LED3);

//Motor Drive output pins   //Mask in output byte
#define L1Lpin D4           //0x01
#define L1Hpin D5           //0x02
#define L2Lpin D3           //0x04
#define L2Hpin D6           //0x08
#define L3Lpin D9           //0x10
#define L3Hpin D10          //0x20

PwmOut L1L(L1Lpin);
PwmOut L1H(L1Hpin);
PwmOut L2L(L2Lpin);
PwmOut L2H(L2Hpin);
PwmOut L3L(L3Lpin);
PwmOut L3H(L3Hpin);

//Mapping from sequential drive states to motor phase outputs
/*
State   L1  L2  L3
0       H   -   L
1       -   H   L
2       L   H   -
3       L   -   H
4       -   L   H
5       H   L   -
6       -   -   -
7       -   -   -
*/

//Drive state to output table
const int8_t driveTable[] = {0x12,0x18,0x09,0x21,0x24,0x06,0x00,0x00};

//Mapping from interrupter inputs to sequential rotor states. 0x00 and 0x07 are not valid
const int8_t stateMap[] = {0x07,0x05,0x03,0x04,0x01,0x00,0x02,0x07};  
const int8_t stateMapReversed[] = {0x07,0x01,0x03,0x02,0x05,0x00,0x04,0x07}; //Alternative if phase order of input or drive is reversed

//Phase lead to make motor spin
volatile int8_t lead = 2;  //2 for forwards, -2 for backwards
volatile float slitTimeMap[] = {0,0,0,0};



//////////////////////
// Global variables //
//////////////////////


volatile float revPerSec = 0; // Instantaneous speed estimate
volatile float slitPosition = 0;
volatile float photoPosition = 0;
volatile float positionEstimate = 0;
volatile float previousTime = 0; // Used to calculate revPerSec
volatile float previousSpeed = 0; // Previous value of revPerSec
volatile float errorPrev = 0.0; //Previous value of error
volatile float integralError = 0.0; //Integral of the error
volatile float dutyCycle = 0.0; // PWM duty cycle between 0 and 1
volatile float timeMap[] = {0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 }; // Keep track of last state
volatile float k = 0.0;
volatile float kd = 0.0;
volatile float ki = 0.0;
Timer timer; // To keep track of time
Serial pc(SERIAL_TX,SERIAL_RX); // Serial connection


///////////////
// Functions //
///////////////

float parseNumber (int position, int *new_pos, char *inPut){
  char number[8];
  int count = position;
  
  while((inPut[count] >= '0' && inPut[count] <= '9') || inPut[count] == '-' || inPut[count] == '.')
  {
      count ++;   
  }
  for (int i = position; i < count; i++)
  {
      number[i-position] = inPut[i];
  }
      number[count] = '\0';
      *new_pos = count;
      return atof(number);  
  } 
void parseTones(char *inPut)
{
    int count = 1;
    while (inPut[count] != 13)
    {
        //Depends on the format of the tone output
        }
    } 

// THREAD: Parse input
void parseRegex(char *inPut, float *speed, float *rev){
    
        int pos_pointer = 0;
        /*
        pc.printf("We got into parsing\r\n");
        for (int f = 0; f < 10; f++)
        {
            pc.printf("%c\n\r", inPut[f]);
        }*/
        switch (inPut[0])
        {
            case 'R':
            //printf("%d\r\n",pos_pointer);
            *rev = parseNumber(1, &pos_pointer, inPut);
            //printf("%d\r\n",pos_pointer);
            if (inPut[pos_pointer] == 'V'){
                //both R and V defined
                *speed = parseNumber(pos_pointer+1, &pos_pointer, inPut);
               // printf("%d\r\n",pos_pointer);
                }
            else if (inPut[pos_pointer] != '\r')
            {
                 pc.printf("Invalid syntax");
                }
            
            break;
            case 'V':
            *speed = parseNumber(1, &pos_pointer, inPut);
            break;
            case 'T':
            parseTones(inPut);
            break;
            default:
            pc.printf("Invalid syntax");
            //wrong format
            break;
            }
        //pc.printf("Revolutions entered: %f, Desired speed: %f\n\r", *rev, *speed);
        
    }

// THREAD: Print instantaneous speed
void printStatus() {
    while(1){
        led3 = !led3;
        pc.printf("%f\n\r",revPerSec);
        wait(2);
    }
}

// THREAD: Control loop
void controlSpeed(float *targetSpeed){
    while(true){
        if (revPerSec > 300){
            revPerSec = 0;
        }
        if (*targetSpeed<=2.0){
            k = 10;
            
        }
        //pc.printf("Target speed: %f\n\r", revPerSec );
        float error = *targetSpeed - revPerSec;
        float errorDer = (error - errorPrev);
        integralError += error;
        /*
        float k = 0.6;
        float kd = 0.0;
        float ki = 0.00115;
        */
        dutyCycle = k*error + ki*integralError;

        if (*targetSpeed<=2.0){
            
            if (dutyCycle>0.3){
                dutyCycle = 0.3;
            }
        }
        //pc.printf("Error: %f\n\r", error );
        errorPrev = error; //remeber error
        wait(0.01);
    }
}

// THREAD: Control loop
void controlPosition(float *rev){
    while(true){
        positionEstimate = photoPosition + slitPosition;
        float error = *rev - positionEstimate;
        float errorDer = (error - errorPrev);
        
        float limit = 0.5;
        if (error < 50.0){k = 10.0; limit = 0.21;}
        dutyCycle = k*error + kd*errorDer;
        //if (dutyCycle < 0) {lead = -2; led1 = 0;} else {lead = 2; led1 = 1;}
        if (dutyCycle > limit) {dutyCycle = limit;}
        errorPrev = error; //remeber error
        wait(0.001);
    }
}

// Measure speed using slits
void measureSpeedSlits(){
    float currentTime = timer.read();
    float timeDiff = (currentTime - slitTimeMap[CHAR + CHBR*2]);
    if (timeDiff > 0.1)
        {   
            revPerSec = 0;}
    else
        {
        revPerSec = 0.25*previousSpeed + 0.75*((0.008547)/(currentTime-slitTimeMap[CHAR + CHBR*2]));
        }
    if (revPerSec > 4.0){revPerSec = previousSpeed;}
    slitTimeMap[CHAR + CHBR*2] = currentTime;
    previousSpeed = revPerSec;
}


/*
void measurePositionSlits(){
    slitPosition += 0.0021367521;
}
*/
// Measure speed using photointerrupters
void measureSpeedPhoto(){
    //led3 = !led3;
    float speedTime;
    speedTime = timer.read();
    revPerSec = 1.0/(speedTime - timeMap[I1 + 2*I2 + 4*I3]);
    timeMap[I1 + 2*I2 + 4*I3] = speedTime;

    photoPosition += 0.16666666;
    slitPosition = 0.0;
}          

/*void measurePositionPhoto(){
    photoPosition += 0.16666666;
    slitPosition = 0.0;
}  */  
    
// Set motor states
void motorOut(int8_t driveState, float dutyCycle){
    //Lookup the output byte from the drive state.
    int8_t driveOut = driveTable[driveState & 0x07];
      
    //Turn off first
    if (~driveOut & 0x01) L1L.write(0);         // = 0
    if (~driveOut & 0x02) L1H.write(dutyCycle); // = 1;
    if (~driveOut & 0x04) L2L.write(0);         // = 0;
    if (~driveOut & 0x08) L2H.write(dutyCycle); // = 1;
    if (~driveOut & 0x10) L3L.write(0);         // = 0;
    if (~driveOut & 0x20) L3H.write(dutyCycle); // = 1;
    
    //Then turn on
    if (driveOut & 0x01) L1L.write(dutyCycle);  // = 1;
    if (driveOut & 0x02) L1H.write(0);          // = 0;
    if (driveOut & 0x04) L2L.write(dutyCycle);  // = 1;
    if (driveOut & 0x08) L2H.write(0);          // = 0;
    if (driveOut & 0x10) L3L.write(dutyCycle);  // = 1;
    if (driveOut & 0x20) L3H.write(0);          // = 0;
}
    
//Convert photointerrupter inputs to a rotor state
inline int8_t readRotorState(){
    //if (lead > 0){
    return stateMap[I1 + 2*I2 + 4*I3];//}
    //else {return stateMapReversed[I1 + 2*I2 + 4*I3];}
    //return stateMap[I1 + 2*I2 + 4*I3];
}

//Basic synchronisation routine    
int8_t motorHome() {
    //Put the motor in drive state 0 and wait for it to stabilise
    motorOut(0,1);
    wait(3.0);
    
    //Get the rotor state
    return readRotorState();
}


//////////
// Main //
//////////     

int main() {
    
    // Initialize threads
    Thread speedControlThread(osPriorityNormal, DEFAULT_STACK_SIZE/2);
    Thread positionControlThread(osPriorityNormal, DEFAULT_STACK_SIZE/4);
    Thread playTones(osPriorityNormal, DEFAULT_STACK_SIZE/4);

    timer.start();
    
    //Initialize the serial port
    Serial pc(SERIAL_TX, SERIAL_RX);
    pc.printf("Device on \n\r");
    
    int8_t orState = 0;    //Rotot offset at motor state 0
    int8_t intState = 0;
    int8_t intStateOld = 0;
    
    float PWM_period = 0.001f; 

    L1L.period(PWM_period);
    L1H.period(PWM_period);
    L2L.period(PWM_period);
    L2H.period(PWM_period);
    L3L.period(PWM_period);
    L3H.period(PWM_period);
    
    // Slits interrupts
    CHAintr.rise(&measureSpeedSlits);
    CHBintr.rise(&measureSpeedSlits);
    CHAintr.fall(&measureSpeedSlits);
    CHBintr.fall(&measureSpeedSlits);

    I1intr.rise(&measureSpeedPhoto);
    I2intr.rise(&measureSpeedPhoto);
    I3intr.rise(&measureSpeedPhoto);
    I1intr.fall(&measureSpeedPhoto);
    I2intr.fall(&measureSpeedPhoto);
    I3intr.fall(&measureSpeedPhoto);
    
    //Run the motor synchronisation
    //orState = motorHome();
    
    // USE FOR PHOTOINTERRUPTERS
    // Photointerrupters interrupts
    
    
    //Poll the rotor state and set the motor outputs accordingly to spin the motor
    while (1) {
        
        // Read serial input
        if (pc.readable()){
            speedControlThread.terminate();
            positionControlThread.terminate();

            CHAintr.disable_irq();
            CHBintr.disable_irq();

            I1intr.disable_irq();
            I2intr.disable_irq();
            I3intr.disable_irq();

            int c = 0;
            char input[50];
            char tmp;
            float rev = 0;
            float speed = 0;
            lead = 2;
            printf("POsition estimate %f\n\r", positionEstimate);
            while ((tmp = pc.getc()) != '\r'){

                input[c] = tmp;
                pc.printf("%c",tmp);
                c++;
            }
            /*
            do{
                tmp = pc.getc();
                input[c] = tmp;
                pc.printf("%c",tmp);
                c++;
            }while(tmp != '\r' || tmp != '\n');
            */
            input[c] = '\r';
            parseRegex(input, &speed, &rev);
            pc.printf("\n\rRevolutions entered: %f, Desired speed: %f\n\r", rev, speed);
            
            /*
            orState = motorHome();
            intState = 0;
            intStateOld = 0;
            integralError = 0.0;
            revPerSec = 0.0;
           
            timeMap[0] = timeMap[1] = timeMap[2] =timeMap[3] =timeMap[4] = timeMap[5] = 0;
            */
            //timer.reset();
            //
            
            if (rev < 0 || speed < 0){
                lead = -2;
            }
            
            rev = abs(rev);
            speed = abs(speed);
            
            if (rev == 0.0 && speed != 0.0){
                //pc.printf("We are starting control loop\n\r\n\r\n\r" );
                if (speed <= 2){
                    

                    //I1intr.enable_irq();
                    //I2intr.enable_irq();
                    //I3intr.enable_irq();
                    CHAintr.enable_irq();
                    CHBintr.enable_irq();
                    k = 4;
                    ki = 0.0001;

                //speedControlThread.start(callback(controlSpeed, &speed));
                //pc.printf("Control loop started\n\r" );
                }
                else {

                    
                    I1intr.enable_irq();
                    I2intr.enable_irq();
                    I3intr.enable_irq();
                    if(speed >= 4 && speed <= 8){
                        k = 0.6;
                        ki = 0.00115;
                    }else if(speed >=2 && speed <= 4){
                        k = 0.25;
                        ki = 0.00090;

                    }
                    else if (speed >= 8 && speed <= 12){

                        k = 0.4;
                        ki = 0.00060;

                    }else {
                        k = 0.4;
                        ki = 0.0004*(15/speed);
                    }
                    //speedControlThread.start(callback(controlSpeed, &speed));
                    
                }
            
            orState = motorHome();
            intState = 0;
            intStateOld = 0;
            integralError = 0.0;
            revPerSec = 0.0;
           
            timeMap[0] = timeMap[1] = timeMap[2] =timeMap[3] =timeMap[4] = timeMap[5] = 0;

            speedControlThread.start(callback(controlSpeed, &speed));

            }
            


            else if (rev != 0.0 && speed == 0.0){
                slitPosition = 0.0;
                photoPosition = 0.0;
                positionEstimate = 0.0;
                     k = 1.0;
                    //kd = 240.0;
                    CHAintr.enable_irq();
                    CHBintr.enable_irq();
                    I1intr.enable_irq();
                    I2intr.enable_irq();
                    I3intr.enable_irq();
                
                orState = motorHome();
                intState = 0;
                intStateOld = 0;
                integralError = 0.0;
                revPerSec = 0.0;
                timeMap[0] = timeMap[1] = timeMap[2] =timeMap[3] =timeMap[4] = timeMap[5] = 0;


                positionControlThread.start(callback(controlPosition, &rev));
            }
        }
        //printf("Motor should be rotating\n\r");
       // pc.printf("%f\n\r",dutyCycle );
        //pc.printf("Control loop started %f ggg %f \n\r", revPerSec, dutyCycle );
        wait(0.001);
        intState = readRotorState();
        if (intState != intStateOld) {
            intStateOld = intState;
            motorOut((intState-orState+lead+6)%6, dutyCycle); //+6 to make sure the remainder is positive
        }
    }
}