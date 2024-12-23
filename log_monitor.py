import json
import requests
import sys
import time
import schedule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
import os
from typing import List, Dict, Optional, Literal, Tuple
from dataclasses import dataclass
from enum import Enum

load_dotenv()

class ControlPlane(str, Enum):
    US = "us"
    EU = "eu1"
    GOV = "gov"

    @property
    def base_url(self) -> str:
        if self == ControlPlane.US:
            return "https://anypoint.mulesoft.com"
        elif self == ControlPlane.EU:
            return "https://eu1.anypoint.mulesoft.com"
        elif self == ControlPlane.GOV:
            return "https://gov.anypoint.mulesoft.com"
        else:
            raise ValueError(f"Invalid control plane: {self}")

@dataclass
class SearchPattern:
    type: str
    search_string: str
    mail: List[str]
    app_name: str

@dataclass
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    sender: str
    use_tls: bool = True

@dataclass
class MulesoftConfig:
    org_id: str
    env_id: str
    control_plane: ControlPlane
    
    @property
    def base_url(self) -> str:
        return f"{self.control_plane.base_url}/cloudhub/api/v2"
    
    @property
    def auth_url(self) -> str:
        return f"{self.control_plane.base_url}/accounts/api/v2/oauth2/token"

class LogMonitor:
    def __init__(self):
        self.client_id = os.getenv('MULESOFT_CLIENT_ID')
        self.client_secret = os.getenv('MULESOFT_CLIENT_SECRET')
        self.check_interval = int(os.getenv('CHECK_INTERVAL_SECONDS', '300'))
        self.verbose_logging = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
        
        # Mulesoft Configuration
        control_plane_str = os.getenv('MULESOFT_CONTROL_PLANE', 'us').lower()
        try:
            control_plane = ControlPlane(control_plane_str)
        except ValueError:
            print(f"Invalid control plane {control_plane_str}, defaulting to US")
            control_plane = ControlPlane.US
            
        self.mulesoft_config = MulesoftConfig(
            org_id=os.getenv('MULESOFT_ORG_ID'),
            env_id=os.getenv('MULESOFT_ENV_ID'),
            control_plane=control_plane
        )
        
        # SMTP Configuration
        self.smtp_config = SMTPConfig(
            host=os.getenv('SMTP_HOST'),
            port=int(os.getenv('SMTP_PORT', '587')),
            username=os.getenv('SMTP_USERNAME'),
            password=os.getenv('SMTP_PASSWORD'),
            sender=os.getenv('SMTP_SENDER'),
        )
        
        # Create last_check directory
        os.makedirs("last_check", exist_ok=True)
        
        # Load search patterns from JSON file
        self.search_patterns = self._load_search_patterns()
        
        self._validate_config()

    def _verbose_log(self, message: str):
        """Helper function for verbose logging."""
        if self.verbose_logging:
            print(message)

    def _load_search_patterns(self) -> List[SearchPattern]:
        patterns_file = os.getenv('PATTERNS_FILE', 'patterns.json')
        try:
            with open(patterns_file, 'r') as f:
                patterns_data = json.load(f)
                return [SearchPattern(**pattern) for pattern in patterns_data]
        except Exception as e:
            sys.exit(f"Error loading search patterns: {e}")

    def _validate_config(self):
        required_vars = [
            'MULESOFT_CLIENT_ID',
            'MULESOFT_CLIENT_SECRET',
            'MULESOFT_ORG_ID',
            'MULESOFT_ENV_ID',
            'SMTP_HOST',
            'SMTP_USERNAME',
            'SMTP_PASSWORD',
            'SMTP_SENDER'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            sys.exit(f"Missing required environment variables: {', '.join(missing)}")

    def send_email(self, recipients: List[str], subject: str, body: str):
        try:
            for recipient in recipients:
                msg = MIMEMultipart()
                msg['From'] = self.smtp_config.sender
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP(self.smtp_config.host, self.smtp_config.port) as server:
                    if self.smtp_config.use_tls:
                        server.starttls()
                    server.login(self.smtp_config.username, self.smtp_config.password)
                    server.send_message(msg)
                    print(f"Email sent to {recipient}")
        except Exception as e:
            print(f"Error sending email: {e}")

    def get_auth_token(self) -> str:
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            response = requests.post(self.mulesoft_config.auth_url, data=data)
            self._verbose_log(f"Auth request URL: {self.mulesoft_config.auth_url}")
            self._verbose_log(f"Auth request data: {data}")
            
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.RequestException as e:
            print(f"Auth request error: {e}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
            sys.exit(1)

    def get_instance_ids(self, app_name: str, auth_token: str) -> List[str]:
        """Recupera gli ID di tutte le istanze dell'applicazione."""
        url = f"{self.mulesoft_config.base_url}/applications/{app_name}/deployments"
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'X-ANYPNT-ENV-ID': self.mulesoft_config.env_id,
            'X-ANYPNT-ORG-ID': self.mulesoft_config.org_id,
            'Content-Type': 'application/json'
        }
        
        try:
            self._verbose_log(f"\nRequest URL: {url}")
            self._verbose_log(f"Request headers: {json.dumps(headers, indent=2)}")
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if self.verbose_logging:
                self._verbose_log(f"Response status: {response.status_code}")
                self._verbose_log(f"Response data: {json.dumps(data, indent=2)}")
            
            # Prendi l'ultimo deployment
            last_deployment = data['data'][-1]
            
            # Prendi tutti gli instance IDs
            instance_ids = []
            for instance in last_deployment['instances']:
                instance_id = instance.get('instanceId')
                if instance_id:
                    instance_ids.append(instance_id)
            
            return instance_ids
                
        except Exception as e:
            print(f"Error getting instance IDs for {app_name}: {e}")
            return []

    def get_log_url(self, app_name: str, instance_id: str) -> str:
        """Costruisce l'URL per il recupero dei log."""
        return (f"{self.mulesoft_config.base_url}/organizations/{self.mulesoft_config.org_id}"
                f"/environments/{self.mulesoft_config.env_id}/applications/{app_name}"
                f"/instances/{instance_id}/log-file")

    def analyze_file(self, auth_token: str, pattern: SearchPattern) -> bool:
        """Analizza i log di tutte le istanze dell'applicazione."""
        try:
            instance_ids = self.get_instance_ids(pattern.app_name, auth_token)
            if not instance_ids:
                print(f"No instances found for {pattern.app_name}")
                return False

            found_matches = False
            for instance_id in instance_ids:
                log_url = self.get_log_url(pattern.app_name, instance_id)
                last_check_date = self._get_last_check_date(pattern.app_name, instance_id)
                
                headers = {
                    'Authorization': f'Bearer {auth_token}',
                    'X-ANYPNT-ENV-ID': self.mulesoft_config.env_id,
                    'X-ANYPNT-ORG-ID': self.mulesoft_config.org_id,
                    'Content-Type': 'application/json'
                }
                
                self._verbose_log(f"\nFetching logs from: {log_url}")
                self._verbose_log(f"Using headers: {json.dumps(headers, indent=2)}")
                
                response = requests.get(log_url, headers=headers, stream=True)
                response.raise_for_status()
                
                worker_match = self._process_log_stream(response, last_check_date, pattern, instance_id)
                print(f"  » {instance_id} (from: {last_check_date or 'start'}) -> {'Match' if worker_match else 'No Match'}")
                if worker_match:
                    found_matches = True
                
            return found_matches
                
        except requests.RequestException as e:
            print(f"Request error for {pattern.app_name}: {e}")
            if hasattr(e, 'response') and self.verbose_logging:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            return False

    def _get_last_check_date(self, app_name: str, instance_id: str) -> Optional[str]:
        """Get last check date for specific application instance."""
        filename = f'last_check/{app_name}_{instance_id}.txt'
        try:
            with open(filename, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def _save_last_check_date(self, app_name: str, instance_id: str, last_date: str):
        """Save last check date for specific application instance."""
        filename = f'last_check/{app_name}_{instance_id}.txt'
        with open(filename, 'w') as f:
            f.write(last_date)

    def _process_log_stream(self, response, last_check_date: Optional[str], pattern: SearchPattern, instance_id: str) -> bool:
        total_size = 0
        total_lines = 0
        last_date = None
        start_checking = last_check_date is None
        pattern_found = False
        
        for line_number, line in enumerate(response.iter_lines(decode_unicode=True), 1):
            if not line:  # Skip empty lines
                continue
                
            total_size += len(line.encode('utf-8'))
            total_lines = line_number
            
            try:
                if "INFO" in line:
                    current_date = self._extract_date(line)
                    if current_date:
                        last_date = current_date
                        if not start_checking and current_date > last_check_date:
                            start_checking = True
                
                if start_checking:
                    if self._check_pattern(line, line_number, last_date, pattern, instance_id):
                        pattern_found = True
                    
            except Exception as e:
                self._verbose_log(f"Error processing line {line_number}: {e}")
                continue
        
        if last_date:
            self._save_last_check_date(pattern.app_name, instance_id, last_date)
            
        return pattern_found

    def _extract_date(self, line: str) -> Optional[str]:
        parts = line.split("INFO", 1)
        if parts and len(parts[0].strip().split()) >= 1:
            return parts[0].strip()
        return None

    def _check_pattern(self, line: str, line_number: int, current_date: str, 
                      pattern: SearchPattern, instance_id: str) -> bool:
        line_normalized = ' '.join(line.split())
        search_normalized = ' '.join(pattern.search_string.split())
        
        if search_normalized in line_normalized:
            self._handle_pattern_match(pattern, line, line_number, current_date, instance_id)
            return True
        return False

    def _handle_pattern_match(self, pattern: SearchPattern, line: str, line_number: int, 
                            current_date: str, instance_id: str):
        print(f"  » Match found [{pattern.type}]: {line}")
        
        subject = f"Log Alert: {pattern.type} - {pattern.app_name}"
        body = f"""
Alert Details:
Application: {pattern.app_name}
Worker: {instance_id}
Control Plane: {self.mulesoft_config.control_plane.value}
Environment: {self.mulesoft_config.env_id}
Type: {pattern.type}
Pattern: {pattern.search_string}

Log Entry:
{line}

Time: {current_date}
"""
        self.send_email(pattern.mail, subject, body)

    def check_files(self):
        """Check logs for all configured applications."""
        try:
            auth_token = self.get_auth_token()
            found_matches = False
            total_patterns = len(self.search_patterns)
            
            for index, pattern in enumerate(self.search_patterns, 1):
                print(f"\nPattern {index}/{total_patterns} - Monitoring {pattern.app_name} [{len(self.get_instance_ids(pattern.app_name, auth_token))} workers]")
                if self.analyze_file(auth_token, pattern):
                    found_matches = True
            
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check completed - New matches: {'Yes' if found_matches else 'No'}")
        except Exception as e:
            print(f"Error during check: {e}")
            if hasattr(e, '__traceback__') and self.verbose_logging:
                import traceback
                traceback.print_exc()


    def run(self):
        """Start the monitoring process"""
        print(f"\nMulesoft Log Monitor started")
        print(f"Control Plane: {self.mulesoft_config.control_plane.value}")
        print(f"Environment: {self.mulesoft_config.env_id}")
        print(f"Check interval: {self.check_interval}s")
        print(f"Applications: {', '.join(p.app_name for p in self.search_patterns)}\n")
        
        self.check_files()  # Initial check
        schedule.every(self.check_interval).seconds.do(self.check_files)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping monitor...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                if hasattr(e, '__traceback__'):
                    import traceback
                    traceback.print_exc()
                time.sleep(self.check_interval)

def main():
    try:
        monitor = LogMonitor()
        monitor.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()