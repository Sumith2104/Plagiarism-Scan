import os, sys
os.chdir(r'c:\Users\hariv\Downloads\Plagiarism-Scan-main\Plagiarism-Scan-main\backend')
sys.path.insert(0, '.')

from app.core.detection import DetectionEngine

ai_text = (
    "Artificial intelligence (AI) is transforming numerous industries by enabling machines to perform tasks that "
    "traditionally required human intelligence. Furthermore, machine learning algorithms have demonstrated remarkable "
    "capabilities in pattern recognition and data analysis. Moreover, deep learning models, particularly neural networks, "
    "have achieved unprecedented levels of accuracy in image classification tasks. Additionally, natural language processing "
    "has enabled computers to understand and generate human language with increasing sophistication. Consequently, businesses "
    "are leveraging AI to enhance productivity, reduce costs, and improve customer experiences. It is important to note that "
    "ethical considerations play a crucial role in the responsible development and deployment of AI systems. In conclusion, "
    "the continued advancement of artificial intelligence presents both significant opportunities and important challenges."
)

human_text = (
    "I went to the store yesterday and it was so annoying! They were out of my favorite cereal AGAIN. "
    "I don't know why this keeps happening. Ugh. Anyway, I ended up buying some granola bars instead. "
    "My friend Dave called while I was there - he wants to grab lunch tomorrow. I haven't seen him in ages! "
    "Things have been crazy busy lately with the new project at work. Can't believe it's already June."
)

eng = DetectionEngine.__new__(DetectionEngine)

r_ai = eng._detect_ai_content(ai_text)
print("AI paragraph  -> score:", r_ai["ai_probability"], "| label:", r_ai["label"])

r_human = eng._detect_ai_content(human_text)
print("Human paragraph -> score:", r_human["ai_probability"], "| label:", r_human["label"])
