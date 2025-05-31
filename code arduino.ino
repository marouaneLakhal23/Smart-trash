#include <SoftwareSerial.h>
#include <NewPing.h>


SoftwareSerial gsmSerial(7, 8); // TX = pin7 , RX= pin 8

int pinTrig = 2; // pin 2 TRIG capteur
int pinEcho = 3; // pin 3 ECHO capteur
int pourcentage = 0; // initialisation 
long temps;
float distance;
NewPing sonar(pinTrig, pinEcho, 400);   //distance max du capteur 4m(datasheet)

// Initialiser la communication série
void setup() {
  gsmSerial.begin(9600);   //vitesse de transmission a envoyer au sim900A
  Serial.begin(9600);     // vitesse d'affichage du moniteur 
  delay(1000);
}

// Boucle principale
void loop() {
 
  temps = sonar.ping(); // calcul du temps entre l'emission et la recepetion
  
 
    distance = (temps * 0.0343) / 2;  // Calcul de la distance en cm

    if (distance <= 30) {
      pourcentage = 100;  // Poubelle remplie (distance < 30 cm)
    } else if (distance >= 400) {
      pourcentage = 0;    // Poubelle vide (distance > 400 cm)
    } else {
      pourcentage = 100 - ((distance - 30) * 100.0 / (400 - 30)); // calcul pourcentage entre 0 et 100%
    }

    Serial.print("Remplissage: "); 
    Serial.print(pourcentage);  //affichage valeur
    Serial.println(" %");

    // Envoi du pourcentage à ThingSpeak
    ConnexionServeur();
    Envoie(pourcentage);// envoie pourcentage a ThingSpeak
    Fin_de_transmission();
  

  delay(2000);  // envoie 1 donnée chaque minute
}

// Fonctions AT et HTTP
void ShowSerialData() {
  while (gsmSerial.available()) {
    Serial.write(gsmSerial.read());
  }
}

void ConnexionServeur() {
  gsmSerial.println("AT");   
  delay(200);
  ShowSerialData();

  gsmSerial.println("AT+CREG?");      
  delay(200);  
  ShowSerialData();

  gsmSerial.println("AT+CGATT?");     
  delay(200);  
  ShowSerialData();

  gsmSerial.println("AT+CIPSHUT");    
  delay(200); 
  ShowSerialData(); // reset IP
  gsmSerial.println("AT+CIPSTATUS");  
  delay(1000); 
  ShowSerialData();

  gsmSerial.println("AT+CIPMUX=0");  
  delay(1000); 
  ShowSerialData(); // single IP

  gsmSerial.println("AT+CSTT=\"internet.orange.ma\""); // APN de l'opérateur
  delay(200);  
  ShowSerialData();

  gsmSerial.println("AT+CIICR");      
  delay(2000); 
  ShowSerialData(); // bring up wireless

  gsmSerial.println("AT+CIFSR");      
  delay(2000); 
  ShowSerialData(); // get IP

  gsmSerial.println("AT+CIPSPRT=0");  
  delay(1000); 
  ShowSerialData(); // disable prompt

  gsmSerial.println("AT+CIPSTART=\"TCP\",\"api.thingspeak.com\",\"80\""); // Connexion GPRS
  delay(2000); 
  ShowSerialData();

  gsmSerial.println("AT+CIPSEND");    
  delay(2000); 
  ShowSerialData(); // Passer en mode d'envoi
}

void Envoie(int data) {
  String str  = "GET /update?api_key=UFKASL6BMIRIASRA";
  str        += "&field1=";
  str        += String(data);  
  str        += " HTTP/1.0\r\nHost: api.thingspeak.com\r\n\r\n";

  gsmSerial.println(str);   // Envoi de la requête
  delay(2000); 
  ShowSerialData();

  gsmSerial.write((char)26);  
  delay(4000);  
  ShowSerialData();
  gsmSerial.println();        
}

void Fin_de_transmission() {
  gsmSerial.println("AT+CIPCLOSE");   // Ferme la connexion
  delay(1000); ShowSerialData();
  gsmSerial.println("AT+CIPSHUT");    // Libère le contexte
  delay(1000); ShowSerialData();
   gsmSerial.println("AT+CSCLK=1");  //mode veille
   delay(60000);
   gsmSerial.println("AT+CSCLK=0");//reveiller 
}
