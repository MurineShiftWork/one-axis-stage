// Dependencies:
//  Dynamixel2Arduino library from ROBOTIS, v0.8.0
#include <Dynamixel2Arduino.h>

#define DEBUG_PRINT 0                                                      // Enable debug print statements
#define OUTPUT_TTL 0                                                       // whether to output TTLs while moving
#define dxl_serial Serial                                                  // Dynamixel communication port
#define cmd Serial2                                                        // Command input port
#define dxl_protocol_version 2.0                                           // Dynamixel protocol version, as float 1.0 or 2.0
#define dxl_dir_pin 2                                                      // Direction control pin
#define dxl_baudrate 115200                                                // Dynamixel baud rate
#define cmd_baudrate 115200                                                // Command input baud rate
#define move_ttl_pin 30                                                    // TTL pin for move indication
#define MAX_ID 253                                                         // Maximum Dynamixel ID to scan
#define MOVE_TIMEOUT 1000                                                  // Timeout duration in milliseconds
#define MOVE_QUERY_INTERVAL 5                                              // Interval to query position in milliseconds
#define TARGET_TOLERANCE 10                                                 // Tolerance in position units
#define MAX_BAUD 5                                                         // Number of baud rates to scan
const int32_t buad[MAX_BAUD] = {57600, 115200, 1000000, 2000000, 3000000}; // Baud rates to scan

Dynamixel2Arduino dxl(dxl_serial, dxl_dir_pin); // Dynamixel object
using namespace ControlTableItem;

void setup()
{
    // Initialize command communication
    cmd.begin(cmd_baudrate);
    while (!cmd)
        ;

    // Initialize Dynamixel communication
    dxl.begin(dxl_baudrate);
    dxl.setPortProtocolVersion(dxl_protocol_version);

    // Initialize move indication pin
    pinMode(move_ttl_pin, OUTPUT);
    digitalWrite(move_ttl_pin, LOW); // Set TTL pin low initially
}

void loop()
{
    static byte startByte = '<';
    static byte stopByte = '>';
    static byte commandChar;
    // static uint16_t int1;
    // static uint16_t int2;

    static bool receiving = false;
    static byte buffer[256];
    static int bufferIndex = 0;

    // Check if data is available
    while (cmd.available())
    {
        byte incomingByte = cmd.read();

        if (incomingByte == startByte)
        {
            // Start receiving message
            receiving = true;
            bufferIndex = 0;
            continue;
        }

        // EVAL: Stop receiving message and process data
        if (incomingByte == stopByte)
        {
            receiving = false;
            commandChar = buffer[0];

            switch (commandChar)
            // Command API
            // SET
            //
            //  move one                     device id (int)       position raw (int)   -> None
            //  move multiple                [(id, pos), (id, pos), ...]                -> None
            //
            //  new baudrate                 device id (int)        baudrate (int)      -> success (bool)
            //  new id                       device id (int)        new id (int)        -> success (bool)
            //  flash                        device id (int)        other specs for flash  -> None
            //  set velocity                 device id (int)        new velocity (int)      -> success (bool)
            //  set operating mode           device id (int)        mode (str)          -> success (bool)
            //
            // GET
            //
            //  get info one                 device id              -> str: dict of info
            //  get info all                 list of IDs            -> str: list of dicts for info on each device
            //  scan all                                            -> str: list of dicts for info on each device
            {
            // GETTERS
            case 's': // Scan for devices
                if (DEBUG_PRINT)
                    Serial.println("about to scan for devices...");

                scanForDevices();
                break;

            case 'i': // Get info one
                // getInfoOne(int1);  // TODO
                break;

            case 'I': // Get info all
                // getInfoAll();      // TODO
                break;

            case 'p':
                // Get position
                // Expecting at least one character + one integer (2 bytes)
                if (bufferIndex >= 3)
                {
                    uint16_t id = (buffer[1] << 8) | buffer[2]; // Combine two bytes to form integer
                    getPosition(id);
                }
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'p'");
                }
                break;

            // SETTERS
            case 'm':                 // Move device
                if (bufferIndex >= 5) // Expecting at least one character + two integers (2 bytes each) -> 5 bytes
                {
                    // Unpack the message
                    // commandChar = buffer[0];
                    uint16_t id = (buffer[1] << 8) | buffer[2];       // Combine two bytes to form integer
                    uint16_t position = (buffer[3] << 8) | buffer[4]; // Combine two bytes to form integer

                    moveDevice(id, position);

#if OUTPUT_TTL
                    digitalWrite(move_ttl_pin, HIGH);
                        // Wait for the move to complete or timeout
                        unsigned long startTime = millis();
                        while (millis() - startTime < MOVE_TIMEOUT)
                        {
                            int currentPosition = dxl.getPresentPosition(id, UNIT_RAW);

                            if (abs(currentPosition - position) <= TARGET_TOLERANCE)
                            {
                                break; // Target reached within tolerance
                            }
                            delay(MOVE_QUERY_INTERVAL); // Small delay to avoid busy waiting
                        }
                        digitalWrite(move_ttl_pin, LOW);
#endif

                }//end: m
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'm'");
                }
                break;
                // todo: other commands:
                // s=scan, k=move multiple, p=get position, i=get info one, a=get info all,
                // f=flash, b=baudrate, i=set id, v=set velocity, o=mode,

            case 'M':
                // Move multiple devices
                // Expecting at least one character + pairs of two integers (2 bytes each)
                if (bufferIndex >= 5 && (bufferIndex - 1) % 4 == 0)
                {
                    // for each tuple of (device id, target position)
                    for (int i = 1; i < bufferIndex; i += 4)
                    {
                        uint16_t id = (buffer[i] << 8) | buffer[i + 1];           // Combine two bytes to form integer
                        uint16_t position = (buffer[i + 2] << 8) | buffer[i + 3]; // Combine two bytes to form integer

                        moveDevice(id, position);

#if DEBUG_PRINT
                        Serial.print("Moving device ID ");
                        Serial.print(id);
                        Serial.print(" to position ");
                        Serial.println(position);
#endif
                    }//end: tuples
                }//end: M
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'M'");
                }
                break;


            case 'b': // Set baudrate
                // alignAllDevicesBaudrate(int1);
                break;

            case 'd': // Set ID
                // setDeviceId(int1, int2);
                break;

            case 'v': // Set velocity
                // setMaxVelocity(int1, int2);
                break;

            case 'o': // Set mode
                // setDeviceMode(int1, int2);
                break;

            case 'f': // Flash device
                // flashDevice(int1, int2, int3);  // (id, duration, repeats)
                break;

            default:
                if (DEBUG_PRINT)
                    Serial.println("Invalid command");
                break;
            }
        } // EVAL

        // RX
        if (receiving)
        {
            // Store received bytes in buffer
            if (bufferIndex < sizeof(buffer))
            {
                buffer[bufferIndex++] = incomingByte;
            }
        } // RX
    } // while
} // loop

void moveDevice(uint16_t id, uint16_t position)
{
    // Check if ID is within valid range
    if (id < 1 || id > MAX_ID)
    {
        if (DEBUG_PRINT)
            Serial.println("Invalid ID");
        return;
    }

    digitalWrite(move_ttl_pin, HIGH);

    // Move the Dynamixel device
    dxl.setGoalPosition(id, position);

    if (DEBUG_PRINT)
    {
        Serial.print("Moving device ID ");
        Serial.print(id);
        Serial.print(" to position ");
        Serial.println(position);
    }
}

void getPosition(int id)
{
    int positionRaw = dxl.getPresentPosition(id, UNIT_RAW);
    // cmd.println(positionRaw);
    cmd.write((positionRaw >> 8) & 0xFF); // Send high byte
    cmd.write(positionRaw & 0xFF);        // Send low byte
}


void scanForDevices() {
  cmd.println("DEBUG: Scanning for devices.");

  int8_t found_dynamixel = 0;

  for(int8_t protocol = 2; protocol < 3; protocol++) {
    dxl.setPortProtocolVersion((float)protocol);
    cmd.print("DEBUG:SCAN PROTOCOL ");
    cmd.println(protocol);

    for(int8_t index = 0; index < MAX_BAUD; index++) {
      cmd.print("DEBUG:SCAN BAUDRATE ");
      cmd.println(buad[index]);
      dxl.begin(buad[index]);

      // Allow time for devices to initialize
      delay(10); // 1 second delay to stabilize communication

      for(int id = 0; id <= MAX_ID; id++) {
        if(dxl.ping(id)) {
          cmd.print("DEBUG: ID : ");
          cmd.print(id);
          cmd.print(", Model Number: ");
          cmd.println(dxl.getModelNumber(id));
          found_dynamixel++;
        }
      }
    }
  }

  cmd.print("DEBUG: Total ");
  cmd.print(found_dynamixel);
  cmd.println(" DYNAMIXEL(s) found!");

  // return to state prior to looping baud rates, etc.
  dxl.begin(dxl_baudrate);
  dxl.setPortProtocolVersion(dxl_protocol_version);
}
