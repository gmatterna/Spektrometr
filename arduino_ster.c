const int ledPins[] = {2, 3, 4, 5, 6, 7, 8};  
const int photodiodePin = A0;  
char command = 'N';  
bool measuring = false;

void setup() {
  Serial.begin(9600);  
  for (int i = 0; i < 7; i++) {
    pinMode(ledPins[i], OUTPUT);
  }
}

void loop() {
  if (Serial.available() > 0) {
    command = Serial.read();
    measuring = (command == 'S' || command == 'R' || command == 'P');
  }

  if (measuring) {
    if (command == 'S') {
      for (int i = 0; i < 30; i++) {  
        int rawValue = analogRead(photodiodePin);
        float voltage = (rawValue / 1023.0) * 5.0;
        Serial.println(voltage, 3);  
        delay(100);
      }
      Serial.println("Koniec pomiaru szumu");
    } else {
      for (int i = 0; i < 7; i++) {
        digitalWrite(ledPins[i], HIGH);
        delay(100);
        int rawValue = analogRead(photodiodePin);
        float voltage = (rawValue / 1023.0) * 5.0;  
        Serial.print(i);             
        Serial.print(",");
        Serial.println(voltage, 3);   
        digitalWrite(ledPins[i], LOW);
        delay(500);
      }
      Serial.println("Koniec pomiaru");
    }
    measuring = false;  
  }
}
