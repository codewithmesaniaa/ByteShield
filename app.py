from difflib import SequenceMatcher
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import re
import javalang
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from itertools import zip_longest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('all-MiniLM-L6-v2')
app = Flask(__name__)
CORS(app)

# ---------------- PREPROCESSING ---------------- #

def preprocess_code(code):
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    code = code.lower()
    code = re.sub(r'\d+', 'num', code)
    code = re.sub(r'"[^"]*"', 'str', code)
    return code


def tokenize(code):
    tokens = re.split(r'\W+', code)

    IGNORE = {
        "var", "num", "str",
        "public", "static", "void", "main",
        "system", "out", "println",
        "class", "args"
    }

    filtered = [
        t for t in tokens
        if t and t not in IGNORE and len(t) > 2
    ]

    return set(filtered)


# ---------------- SIMILARITY ---------------- #

def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def cosine_sim(text1, text2):
    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf)[0][1]


def verdict_from_score(score):
    if score < 30:
        return "Low Similarity"
    elif score < 60:
        return "Medium Similarity"
    else:
        return "High Similarity"


# ---------------- AST FUNCTIONS ---------------- #

def extract_ast_tokens(code):
    tokens = []
    try:
        tree = javalang.parse.parse(code)
        for path, node in tree:
            tokens.append(type(node).__name__)
    except:
        pass  # ignore parsing errors
    return tokens


def ast_similarity(code1, code2):
    tokens1 = set(extract_ast_tokens(code1))
    tokens2 = set(extract_ast_tokens(code2))

    if not tokens1 or not tokens2:
        return 0

    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


# ---------------- LOGIC NORMALIZATION ---------------- #
def detect_code_type(code):
    code = code.lower()

    types = set()

    if re.search(r'\bstring\b', code):
        types.add("string")

    if "int" in code or "double" in code or "float" in code:
        types.add("numeric")

    if "for" in code or "while" in code:
        types.add("loop")

    if "if" in code:
        types.add("condition")

    return types

def normalize_logic(line):
    line = re.sub(r'\b(public|private|static|void|class|int|string|double|float)\b', '', line)
    line = re.sub(r'\b[a-zA-Z_]\w*\b', 'var', line)
    line = re.sub(r'\d+', 'num', line)
    return line.strip()


# ---------------- WORD DIFF ---------------- #

def highlight_diff(line1, line2):
    matcher = SequenceMatcher(None, line1.split(), line2.split())

    result1 = ""
    result2 = ""

    words1 = line1.split()
    words2 = line2.split()

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":
            result1 += " " + " ".join(words1[i1:i2])
            result2 += " " + " ".join(words2[j1:j2])

        else:
            result1 += " " + " ".join(
                [f"<span class='diff'>{w}</span>" for w in words1[i1:i2]]
            )
            result2 += " " + " ".join(
                [f"<span class='diff'>{w}</span>" for w in words2[j1:j2]]
            )

    return result1.strip(), result2.strip()

# ---------------- LINE COMPARISON ---------------- #

def line_by_line_similarity(code1, code2):
    lines1 = [l.strip() for l in code1.split('\n') if l.strip()]
    lines2 = [l.strip() for l in code2.split('\n') if l.strip()]

    result = []

    for line1 in lines1:
        best_match = ""
        best_score = 0

        norm1 = normalize_logic(line1)

        for line2 in lines2:
            norm2 = normalize_logic(line2)

            score = SequenceMatcher(None, norm1, norm2).ratio()

            if score > best_score:
                best_score = score
                best_match = line2

        similarity = round(best_score * 100, 2)

        if similarity >= 85:
            h1, h2 = highlight_diff(line1, best_match)
            highlight = True
        else:
            h1, h2 = line1, best_match
            highlight = False

        result.append({
            "line1": h1,
            "line2": h2,
            "highlight": highlight
        })

    return result

# ---------------- EMBEDDINGS---------------- #

def embedding_similarity(code1, code2):
    try:
        emb = model.encode([code1, code2])   # encode both together (faster)
        return cosine_similarity([emb[0]], [emb[1]])[0][0]
    except:
        return 0

# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/details")
def details():
    return render_template("details.html")


@app.route("/check_similarity", methods=["POST"])
def check_similarity():
    file1 = request.files.get("file1")
    file2 = request.files.get("file2")

    if not file1 or not file2:
        return jsonify({"error": "Two files are required"}), 400

    code1 = file1.read().decode("utf-8")
    code2 = file2.read().decode("utf-8")

    cleaned1 = preprocess_code(code1)
    cleaned2 = preprocess_code(code2)

    tokens1 = tokenize(cleaned1)
    tokens2 = tokenize(cleaned2)

    jac = jaccard_similarity(tokens1, tokens2) * 100
    cos = cosine_sim(cleaned1, cleaned2) * 100
    ast_sim = ast_similarity(code1, code2) * 100

   

    # ---------------- EMBEDDING (OPTIMIZED) ---------------- #

    emb_sim = 0
    # Skip useless cases 
    if jac < 15 and ast_sim < 15:
        emb_sim = 0
    else:
    # Only run embeddings for smaller code
        if len(code1) < 800 and len(code2) < 800:
            emb_sim = embedding_similarity(code1, code2) * 100

     # 🔥 FINAL SCORE
    final_score = (
    0.5 * jac +
    0.3 * ast_sim +
    0.15 * cos +
    0.05 * emb_sim      # small weight (important)
)

    type1 = detect_code_type(code1)
    type2 = detect_code_type(code2)

    # 🔻 Penalize different logic types
    if type1 != type2:
        final_score *= 0.6

    # 🔻 Extra penalty for weak similarity
    if jac < 20 and ast_sim < 20:
        final_score *= 0.5

    verdict = verdict_from_score(final_score)

    line_matches = line_by_line_similarity(cleaned1, cleaned2)

    return jsonify({
        "cosine_similarity": round(cos, 2),
        "jaccard_similarity": round(jac, 2),
        "ast_similarity": round(ast_sim, 2),
        "final_similarity": round(final_score, 2),
        "verdict": verdict,
        "line_matches": line_matches
    })


if __name__ == "__main__":
    app.run(debug=True)