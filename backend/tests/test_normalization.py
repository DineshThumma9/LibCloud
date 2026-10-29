from app.constants import SLUG_MAP
from app.parser import DependencyParser


class TestCacheKeyConsistency:
    def test_cache_keys_match(self):
        for tech in ["GitHub Actions", "PostgreSQL", "ChromaDB", "Pinecone"]:
            slug = SLUG_MAP.get(tech, tech).lower()
            assert slug.islower()
            assert not slug.startswith(" ")


class TestConstantsFixes:
    def test_slug_map_brand_corrections(self):
        assert SLUG_MAP["OkHttp"] == "square"
        assert SLUG_MAP["Google Gemini"] == "googlegemini"
        assert SLUG_MAP["Radix UI"] == "radixui"
        assert SLUG_MAP["Werkzeug"].endswith("werkzeug-icon.svg")
        assert SLUG_MAP["Node.js"] == "nodedotjs"
        assert SLUG_MAP["HeroUI"] == "heroui"
        assert "Tabler Icons" not in SLUG_MAP
        assert "Nomic Foundation" not in SLUG_MAP

    def test_go_subpackage_noise_filtering(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("github.com/stretchr/testify/assert", "go.mod")
        assert res is None and lang is None

        res, lang = parser.normalize_pkg("github.com/stretchr/testify/require", "go.mod")
        assert res is None and lang is None

    def test_next_themes_normalization(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("next-themes", "package.json")
        assert res == "Next.js"
        assert lang == "ts"

    def test_neondatabase_normalization(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("@neondatabase/serverless", "package.json")
        assert res == "PostgreSQL"
        assert lang == "ts"

    def test_elasticsearch_java_normalization(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("co.elastic.clients:elasticsearch-java", "pom.xml")
        assert res == "Elasticsearch"
        assert lang == "java"

    def test_neo4j_casing_consistency(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("langchain-neo4j", "pyproject.toml")
        assert res == "Neo4j"
        assert lang == "py"

    def test_kotlin_jpa_consistency(self):
        parser = DependencyParser()
        res, lang = parser.normalize_pkg("spring-boot-starter-data-jpa", "build.gradle.kts")
        assert res == "JPA / Hibernate"
        assert lang == "kotlin"


class TestTechnologyNormalization:
    def test_new_technology_normalizations(self):
        parser = DependencyParser()

        cases = [
            ("langchain-checkpoint-postgres", "pyproject.toml", "PostgreSQL", "py"),
            ("langchain-redis", "pyproject.toml", "Redis", "py"),
            ("langchain-mcp-adapters", "pyproject.toml", "MCP", "py"),
            ("mcp-server-qdrant", "pyproject.toml", "Qdrant", "py"),
            ("mcp", "pyproject.toml", "FastMCP", "py"),
            ("sse-starlette", "pyproject.toml", "Starlette", "py"),
            ("uvloop", "pyproject.toml", "libuv", "py"),
            ("python-jose", "pyproject.toml", "JWT", "py"),
            ("beautifulsoup4", "pyproject.toml", "Beautiful Soup", "py"),
            ("sockjs-client", "package.json", "SockJS", "ts"),
            ("astryxdesign", "package.json", "Astryx", "ts"),
            ("reportlab", "requirements.txt", "ReportLab", "py"),
            ("tf_keras", "requirements.txt", "Keras", "py"),
            ("tf-keras", "requirements.txt", "Keras", "py"),
            ("urllib3", "requirements.txt", "urllib3", "py"),
            ("@uiw/react-codemirror", "package.json", "CodeMirror", "ts"),
            ("jspdf-autotable", "package.json", "jsPDF", "ts"),
            ("jspdf", "package.json", "jsPDF", "ts"),
            ("postcss", "package.json", "PostCSS", "ts"),
            ("oxlint", "package.json", "Oxlint", "ts"),
            ("djangorestframework", "requirements.txt", "Django", "py"),
            ("pyjwt", "requirements.txt", "JWT", "py"),
            ("moviepy", "requirements.txt", "MoviePy", "py"),
            ("react-native-safe-area-context", "package.json", "React Native", "ts"),
            ("react-native-screens", "package.json", "React Native", "ts"),
            ("react-native-svg", "package.json", "React Native", "ts"),
            ("react-native-web", "package.json", "React Native", "ts"),
            ("eslint-plugin-react", "package.json", "ESLint", "ts"),
            ("eslint-plugin-turbo", "package.json", "ESLint", "ts"),
            ("softprops/action-gh-release", ".github/workflows/deploy.yml", "GitHub Actions", "actions"),
            ("golangci/golangci-lint-action", ".github/workflows/lint.yml", "GitHub Actions", "actions"),
            ("volley", "pom.xml", "Android", "java"),
            ("android-sdk", "pom.xml", "Android", "java"),
            ("solana-sdk", "Cargo.toml", "Solana", "rust"),
            ("solana-program", "Cargo.toml", "Solana", "rust"),
            ("solana-client", "Cargo.toml", "Solana", "rust"),
            ("solana-rpc-client", "Cargo.toml", "Solana", "rust"),
            ("@solana/web3.js", "package.json", "Solana", "ts"),
            ("@solana/spl-token", "package.json", "Solana", "ts"),
            ("@solana-developers/helpers", "package.json", "Solana", "ts"),
            ("eslint-plugin-jsx-a11y", "package.json", "ESLint", "ts"),
            ("react-native-gesture-handler", "package.json", "React Native", "ts"),
            ("ts-mocha", "package.json", "Mocha", "ts"),
            ("hardhat-gas-reporter", "package.json", "Hardhat", "ts"),
            ("vite-plugin-node-polyfills", "package.json", "Vite", "ts"),
            ("react-lottie", "package.json", "Lottie", "ts"),
            ("connect-mongo", "package.json", "MongoDB", "ts"),
            ("multer-storage-cloudinary", "package.json", "Cloudinary", "ts"),
            ("react-spotify-embed", "package.json", "Spotify", "ts"),
            ("react-github-calendar", "package.json", "GitHub", "ts"),
            ("redux-persist", "package.json", "Redux", "ts"),
            ("next-pwa", "package.json", "Next.js", "ts"),
            ("bcrypt-ts", "package.json", "Bcrypt", "ts"),
            ("serde-wasm-bindgen", "Cargo.toml", "Serde", "rust"),
            ("connect-flash", "package.json", "Express", "ts"),
            ("cookieparser", "package.json", "Express", "ts"),
            ("ejs-mate", "package.json", "Express", "ts"),
            ("request-ip", "package.json", "Express", "ts"),
            ("passport-local-mongoose", "package.json", "MongoDB", "ts"),
            ("react-confetti", "package.json", "React", "ts"),
            ("react-cool-inview", "package.json", "React", "ts"),
            ("use-sound", "package.json", "React", "ts"),
            ("react-chartjs-2", "package.json", "Chart.js", "ts"),
            ("werkzeug", "requirements.txt", "Werkzeug", "py"),
            ("multer", "package.json", "Express", "ts"),
            ("method-override", "package.json", "Express", "ts"),
            ("fs", "package.json", "Node.js", "ts"),
            ("expo-constants", "package.json", "Expo", "ts"),
            ("@nextui-org/react", "package.json", "HeroUI", "ts"),
            ("@nomiclabs/hardhat-ethers", "package.json", "nomiclabs", "ts"),
            ("@nomicfoundation/hardhat-ethers", "package.json", "nomiclabs", "ts"),
            ("@tabler/icons-react", "package.json", "Tabler Icons", "ts"),
        ]

        for raw, fname, expected_norm, expected_lang in cases:
            norm, lang = parser.normalize_pkg(raw, fname)
            assert norm == expected_norm, f"Expected {raw} -> {expected_norm}, got {norm}"
            assert lang == expected_lang

    def test_noise_filtering(self):
        parser = DependencyParser()
        noise_samples = [
            ("cors", "package.json"),
            ("cros", "package.json"),
            ("bun-plugin-tailwind", "package.json"),
            ("husky", "package.json"),
            ("cors", "requirements.txt"),
            ("install", "package.json"),
            ("glob", "package.json"),
            ("tls", "package.json"),
            ("db", "package.json"),
            ("simple_asn1", "Cargo.toml"),
            ("zkpdf-lib", "Cargo.toml"),
            ("github.com/peterh/liner", "go.mod"),
            ("github.com/mattn/go-runewidth", "go.mod"),
        ]
        for raw, fname in noise_samples:
            norm, lang = parser.normalize_pkg(raw, fname)
            assert norm is None, f"Expected {raw} in {fname} to be filtered as noise, got {norm}"
