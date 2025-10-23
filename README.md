🕵️‍♂️ Prompt-to-Sketch Generation
AI system for generating forensic sketches from text descriptions


🧠 Project Overview

Prompt-to-Sketch Generation is a deep learning-based project developed to support forensic departments in identifying suspects.
The system can create a sketch of a person’s face just from a written prompt or eyewitness description.
For example, if an officer provides details like “a man in his 30s with curly hair and a beard wearing glasses,” the model will generate a matching sketch.

This project combines Artificial Intelligence, Computer Vision, and Generative Models to help investigators quickly visualize and analyze suspect appearances.


🚀 Key Features

Generates realistic sketches directly from text input.

Supports detailed facial descriptions including features and accessories.

Can be customized or fine-tuned for better accuracy.

Designed for forensic and investigative use cases.

Simple Flask-based web interface for easy testing and visualization.


⚙️ Technology Stack
Category	Tools & Frameworks
Backend	Python (Flask)
AI Model	Stable Diffusion / ControlNet / Custom GAN
Frontend	HTML, CSS, JavaScript (or Streamlit)
Database	MySQL / SQLite (optional)
Version Control	Git & GitHub


🧩 Folder Structure
prompt-to-sketch-generation/
```
│
├── app.py                 # Main application file
├── models/                # AI model files and weights
├── templates/             # HTML templates
├── static/                # CSS and JS assets
├── utils/                 # Helper functions
├── requirements.txt       # Dependencies
└── README.md              # Documentation
```



💡 Working Process

The investigator enters a text prompt describing the suspect.

The model extracts facial attributes and interprets the text.

The AI engine then creates a sketch that matches the prompt.

The output can be saved, modified, or compared with other data.



🧰 How to Run
# Clone this repository
git clone https://github.com/Bheemeshgouda/prompt-to-sketch-generation.git
cd prompt-to-sketch-generation

# Set up environment
python -m venv venv
venv\Scripts\activate      # for Windows


# Install dependencies
pip install -r requirements.txt


# Run the project
python app.py


🖋️ Example Input

“Forensic sketch: Oval face, pointed chin, dark brown short receding hair, high forehead, thick straight eyebrows, almond-shaped close-set dark brown eyes, long hooked nose, hollow cheeks, thin downturned lips, cleft chin, angular jawline, 2-inch vertical left cheek scar, wire-frame glasses, late 40s, stern expression. Black and white line drawing, no shading, front view, clean precise lines”


🧾 The model will generate a sketch resembling the described features.

🔮 Future Improvements

Add voice input to prompt conversion

Support 3D face reconstruction

Add age progression/regression features

Improve sketch detail and accuracy


🤝 Contribution

If you have ideas or improvements, feel free to fork this project and open a pull request.
Suggestions are always welcome!


👨‍💻 Developed By

Bheemesh Gouda
MCA Student | AI & Machine Learning Enthusiast
📧 bheemeshgouda8@gmail.com

