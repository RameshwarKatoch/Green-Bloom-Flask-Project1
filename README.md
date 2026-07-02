# Green Bloom: The Ultimate Technical Archive 🌿

Welcome to the **Green Bloom** repository! Green Bloom is a holistic digital ecosystem designed to redefine how urbanites interact with nature. It is not just another e-commerce site; it brings high-quality flora directly to the doorstep of the modern consumer, focusing on "Seamless Sustainability."

## ✨ Key Features

- **Agentic AI Chatbot**: Built with Groq (Llama-3.1-8b-instant), the chatbot acts as a professional botanist, parsing real-time inventory to recommend plants dynamically.
- **Robust E-commerce Core**: Complete shopping cart functionality, category management (indoor vs outdoor), and persistent cart state.
- **Secure Checkout & Payments**: Integrated with Razorpay for secure transactions with server-side signature verification.
- **Admin Dashboard**: Real-time revenue analytics, inventory control, and order status management.
- **Security Protocols**: Flask-Bcrypt for secure password hashing and Flask-Login for session management.
- **Premium Frontend Design**: Uses "Floral White" and "Rich Saddle Brown" for a premium greenhouse feel, coupled with responsive mobile scaling.

## 🛠 Technology Stack

- **Backend**: Python with Flask
- **Database**: MySQL with SQLAlchemy (ORM)
- **Authentication**: Flask-Bcrypt, Flask-Login
- **AI Integration**: Groq API (Llama-3.1-8b-instant)
- **Payment Gateway**: Razorpay API

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd flown
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Or manually install: `pip install flask sqlalchemy flask-login razorpay flask-admin groq`)*

4. **Environment Variables:**
   Create a `.env` file in the root directory and add your necessary API keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   RAZORPAY_KEY_ID=your_razorpay_key_id
   RAZORPAY_KEY_SECRET=your_razorpay_key_secret
   SECRET_KEY=your_flask_secret_key_here
   ```

5. **Run the Application:**
   ```bash
   python app.py
   ```
   *Note: The app automatically runs `db.create_all()` on the first run, creating your database structure from scratch.*

## 📂 Project Architecture

The application follows the **MVC (Model-View-Controller)** design pattern:
- **Models**: Defines database schemas (User, Product, CartItem, Order, OrderItem) mapping relationships to maintain referential integrity.
- **Views**: HTML templates (`index.html`, `cart.html`, etc.) for rendering the user interface.
- **Controllers**: Flask routes in `app.py` managing the application flow and integrating with Groq for AI parsing.

## 🤝 Conclusion

Green Bloom is more than an app; it's a blueprint for the future of specialized e-commerce. By combining stable, secure backend technologies (Flask/MySQL) with bleeding-edge AI models (Groq/Llama), we've created a store that doesn't just sell—it advises.
