import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Retrieve configurations for debugging
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    
    print("\n" + "="*70)
    print("  [SEC]   DIGITAL EVIDENCE INTEGRITY SYSTEM")
    print("  [LOCK]  AI-Powered Cryptographical Forensic Evidence Management")
    print("  [URL]   URL      : http://127.0.0.1:5000")
    print("  [USER]  Admin    : username: admin        | password: admin123")
    print("  [USER]  Investig.: username: investigator | password: investigator123")
    print("  [USER]  Auditor  : username: auditor      | password: auditor123")
    print("="*70 + "\n")
    
    app.run(host=host, port=port, debug=debug)
