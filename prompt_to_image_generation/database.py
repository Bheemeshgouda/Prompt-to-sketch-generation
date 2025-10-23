from flask_mysqldb import MySQL
from config import Config

mysql = MySQL()

def init_db(app):
    app.config['MYSQL_HOST'] = Config.MYSQL_HOST
    app.config['MYSQL_USER'] = Config.MYSQL_USER
    app.config['MYSQL_PASSWORD'] = Config.MYSQL_PASSWORD
    app.config['MYSQL_DB'] = Config.MYSQL_DB
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    mysql.init_app(app)

def create_tables():
    conn = mysql.connection
    cur = conn.cursor()
    
    # Create tables if they don't exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        full_name VARCHAR(100),
        badge_number VARCHAR(20),
        role ENUM('officer', 'admin') DEFAULT 'officer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id INT AUTO_INCREMENT PRIMARY KEY,
        case_number VARCHAR(50) UNIQUE,
        description TEXT,
        location VARCHAR(100),
        incident_date DATE,
        created_by INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS composites (
        id INT AUTO_INCREMENT PRIMARY KEY,
        case_id INT,
        user_id INT,
        description TEXT NOT NULL,
        image_path VARCHAR(255) NOT NULL,
        is_accurate BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS revisions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        composite_id INT,
        adjustment_text TEXT NOT NULL,
        revised_image_path VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (composite_id) REFERENCES composites(id)
    )
    """)
    
    # Create admin user if not exists
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = cur.fetchone()
    if not admin:
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash('admin123')
        cur.execute(
            "INSERT INTO users (username, password, full_name, badge_number, role) "
            "VALUES (%s, %s, %s, %s, %s)",
            ('admin', password_hash, 'Admin User', '0000', 'admin')
        )
    
    conn.commit()
    cur.close()