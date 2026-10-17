import re 

ICON_CACHE:dict[str,str] = {}


SLUG_MAP = {
    # Java / Spring
    "Spring Boot": "springboot",
    "Spring Security": "springsecurity",
    "WebSockets": "socketdotio",
    "JPA / Hibernate": "hibernate",
    "MongoDB": "mongodb",
    "Neo4j": "neo4j",
    "Redis": "redis",
    "GraphQL": "graphql",
    "OAuth2": "auth0",
    "PostgreSQL": "postgresql",
    "MySQL": "mysql",
    "H2 Database": "h2",
    "OpenAPI / Swagger": "swagger",
    "JWT": "jsonwebtokens",
    "Jackson": "spring",
    "Gson": "google",
    "OkHttp": "okta",
    "Apache HttpClient": "apache",
    "MapStruct": "spring",
    "Apache Kafka": "apachekafka",
    # Python — web
    "FastAPI": "fastapi",
    "Flask": "flask",
    "Django": "django",
    "Starlette": "python",
    "Tornado": "tornado",
    "Uvicorn": "python",
    "Gunicorn": "gunicorn",
    # Python — data / ML
    "SQLAlchemy": "sqlalchemy",
    "Tortoise ORM": "python",
    "Alembic": "python",
    "Qdrant": "qdrant",
    "ChromaDB": "python",
    "Pinecone": "pinecone",
    "Weaviate": "weaviate",
    "NumPy": "numpy",
    "Pandas": "pandas",
    "Polars": "polars",
    "SciPy": "scipy",
    "Scikit-Learn": "scikitlearn",
    "PyTorch": "pytorch",
    "TensorFlow": "tensorflow",
    "Keras": "keras",
    "LightGBM": "lightgbm",
    "XGBoost": "xgboost",
    "CatBoost": "catboost",
    "Optuna": "optuna",
    # Python — LLMs / cloud / misc
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "LangChain": "langchain",
    "LangGraph": "langchain",
    "LlamaIndex": "llamaindex",
    "Hugging Face": "huggingface",
    "Pydantic": "pydantic",
    "Celery": "celery",
    "RQ": "python",
    "Taskiq": "python",
    "HTTPX": "httpx",
    "Requests": "pypi",
    "Aiohttp": "aiohttp",
    "AWS SDK": "awswebservices",
    "Stripe": "stripe",
    "Google Gemini": "googlegemini",
    # JS/TS — frontend frameworks
    "React": "react",
    "Next.js": "nextdotjs",
    "Vue.js": "vuedotjs",
    "Nuxt.js": "nuxtdotjs",
    "Svelte": "svelte",
    "SvelteKit": "svelte",
    "Angular": "angular",
    # JS/TS — backend
    "Express": "express",
    "NestJS": "nestjs",
    "Fastify": "fastify",
    "Koa": "koa",
    "Hono": "hono",
    # JS/TS — UI
    "Tailwind CSS": "tailwindcss",
    "Bootstrap": "bootstrap",
    "Chakra UI": "chakraui",
    "Material UI": "mui",
    "ShadCN": "shadcnui",
    "Styled Components": "styledcomponents",
    "Radix UI": "radixui",
    # JS/TS — state / fetching
    "Redux": "redux",
    "Zustand": "zustand",
    "MobX": "mobx",
    "React Query": "reactquery",
    "SWR": "swr",
    # JS/TS — DB / ORM
    "Prisma": "prisma",
    "Drizzle ORM": "drizzle",
    "TypeORM": "typeorm",
    "Sequelize": "sequelize",
    "Apollo GraphQL": "apollographql",
    "tRPC": "trpc",
    # JS/TS — auth / utils
    "Zod": "zod",
    "Yup": "javascript",
    "Axios": "axios",
    "Socket.io": "socketdotio",
    "Bcrypt": "javascript",
    "Lodash": "lodash",
    "tailwindcss-animate": "tailwindcss",
    "protobuf-java": "google",
    "protobuf": "google",
    # Animation & UI Icons / Utilities
    "GSAP": "greensock",
    "gsap": "greensock",
    "Lucide": "lucide",
    "lucide-react": "lucide",
    "Radix UI": "radixui",
    "radix-ui": "radixui",
    "Vite": "vite",
    "vite": "vite",
    "vitejs": "vite",
    "React Router": "reactrouter",
    "Remark": "remark",
    "Unified": "unified",
    "Astro": "astro",
    "astro": "astro",
    "astrojs": "astro",
}


clean_pkg = {
    "ts": lambda x: x.split("/")[0].strip("@"),
    "java": lambda x: x.split(":")[-1],
}




NOISE_PYTHON = {
    # Testing & mocking
    "pytest", "pytest-cov", "pytest-asyncio", "pytest-mock", "pytest-xdist",
    "pytest-env", "pytest-timeout", "pytest-benchmark", "pytest-randomly",
    "unittest", "mock", "coverage", "hypothesis", "tox", "nox", "factory-boy",
    "faker", "freezegun", "respx", "responses", "httpretty", "vcrpy",
    # Linting, formatting & type checking
    "black", "flake8", "ruff", "isort", "mypy", "pylint", "autopep8",
    "pyright", "pre-commit", "bandit", "safety", "semgrep",
    # types-* stubs (catches all types-X packages)
    "types-requests", "types-setuptools", "types-redis", "types-pyyaml",
    "types-pillow", "types-boto", "types-stripe", "types-python-dateutil",
    # Build & packaging tools
    "typing-extensions", "setuptools", "wheel", "pip", "build",
    "poetry-core", "flit-core", "hatchling", "pdm-backend", "maturin",
    # Low-level transport & platform utilities
    "certifi", "charset-normalizer", "idna", "urllib3", "six",
    "greenlet", "sniffio", "anyio", "async-timeout", "iniconfig",
    "packaging", "platformdirs", "filelock", "multidict", "yarl",
    "frozenlist", "aiosignal", "attrs", "exceptiongroup",
    # Misc runtime noise
    "click",  # CLI helper, rarely the "point" of a project
    "rich", "colorama",  # terminal styling
    "python-dotenv", "environs",  # env var loaders
    "tqdm",  # progress bars
    "h11", "httplib2", "oauthlib", "proto-plus", 
    "pyasn1", "pyasn1_modules", "pyparsing", "annotated-types", "annotated-doc",
    "cachetools", "google-api-core", "google-api-python-client",
    "google-auth-httplib2", "google-auth-oauthlib", "googleapis-common-protos",
}

NOISE_GO = {
    # Testing & assertions
    "github.com/stretchr/testify", "github.com/stretchr/testify/assert",
    "github.com/stretchr/testify/require", "github.com/stretchr/testify/mock",
    "github.com/golang/mock", "go.uber.org/mock",
    "github.com/onsi/ginkgo", "github.com/onsi/gomega",
    # Formatting, linters & tool dependencies
    "golang.org/x/lint", "golang.org/x/tools", "github.com/golangci/golangci-lint",
    # Low-level primitives & sub-packages
    "golang.org/x/sys", "golang.org/x/xerrors", "github.com/davecgh/go-spew",
    "github.com/pmezard/go-difflib",
}

NOISE_TS = {
    # --- @types/* stubs ---
    # clean_pkg strips "@types/" → "types", so one entry catches them all.
    # Individual entries kept for clarity / direct package.json hits.
    "types",
    "@types/node", "@types/react", "@types/react-dom", "@types/jest",
    "@types/express", "@types/cors", "@types/lodash", "@types/supertest",
    "@types/uuid", "@types/bcrypt", "@types/multer", "@types/passport",
    "@types/cookie-parser", "@types/morgan", "@types/compression",
    # Testing
    "jest", "ts-jest", "vitest", "supertest",
    "testing-library",          # @testing-library/* → "testing-library" after clean
    "@testing-library/react", "@testing-library/jest-dom", "@testing-library/user-event",
    # Compilers & type checkers
    "typescript", "ts-node", "tsx", "tsc-alias",
    # Linters & formatters
    "eslint", "prettier",
    "typescript-eslint",        # @typescript-eslint/* → "typescript-eslint" after clean
    "@typescript-eslint/parser", "@typescript-eslint/eslint-plugin",
    "eslint-config-prettier", "eslint-config-next", "eslint-config-airbnb",
    "eslint-plugin-react", "eslint-plugin-react-hooks", "eslint-plugin-import",
    # Build tools & bundlers
    "esbuild", "rollup", "webpack", "webpack-cli", "webpack-dev-server",
    "swc",                      # @swc/* → "swc" after clean
    "babel",                    # @babel/* → "babel" after clean
    "@babel/core", "@babel/preset-env", "@babel/preset-react", "@babel/preset-typescript",
    # CSS tooling & micro-utilities
    "postcss", "autoprefixer",
    "clsx", "class-variance-authority", "tailwind-merge", "globals",
    "eslint-plugin-react-refresh", "tw-animate-css",
    "fontsource-variable", "oxlint", "next-themes", "emotion",
    # Dev utilities
    "nodemon", "ts-node-dev", "concurrently", "rimraf", "cross-env",
    "dotenv", "dotenv-cli", "env-cmd",
    # Runtime shims / low-level
    "tslib", "core-js", "object-assign",
    # Storybook
    "storybook",                # @storybook/* → "storybook" after clean
}

NOISE_JS = {
    # Testing
    "jest", "mocha", "chai", "sinon", "vitest", "cypress",
    "playwright", "puppeteer", "jasmine",
    # Linters, formatters & babel
    "eslint", "prettier", "eslint-config-prettier", "eslint-plugin-react",
    "eslint-plugin-react-hooks", "eslint-plugin-import",
    "babel-loader", "@babel/core", "@babel/preset-env", "@babel/preset-react",
    "babel",                    # @babel/* → "babel" after clean
    # Build & bundlers
    "vite", "vitejs",           # vite / @vitejs/*
    "esbuild", "rollup",
    "webpack", "webpack-cli", "webpack-dev-server",
    "parcel", "turbopack",
    # Dev utilities
    "nodemon", "cross-env", "dotenv", "dotenv-cli",
    "rimraf", "concurrently", "npm-run-all",
    # Low-level polyfills / utils
    "tslib", "core-js", "object-assign",
}


NORM_JAVA = {
    # Spring Boot Starters — web / validation / ops
    "spring-boot-starter-web": "Spring Boot",
    "spring-boot-starter-webflux": "Spring Boot",
    "spring-boot-starter-validation": "Spring Boot",
    "spring-boot-starter-actuator": "Spring Boot",
    "spring-boot-starter-aop": "Spring Boot",
    "spring-boot-starter-cache": "Spring Boot",
    "spring-boot-starter-batch": "Spring Boot",
    "spring-boot-starter-quartz": "Spring Boot",
    # Spring Boot Starters — data
    "spring-boot-starter-data-jpa": "JPA / Hibernate",
    "spring-boot-starter-data-mongodb": "MongoDB",
    "spring-boot-starter-data-neo4j": "Neo4j",
    "spring-boot-starter-data-redis": "Redis",
    "spring-boot-starter-data-elasticsearch": "Elasticsearch",
    "spring-boot-starter-data-cassandra": "Apache Cassandra",
    # Spring Boot Starters — messaging
    "spring-boot-starter-websocket": "WebSockets",
    "spring-boot-starter-amqp": "RabbitMQ",
    "spring-kafka": "Apache Kafka",
    "kafka-clients": "Apache Kafka",
    # Spring Boot Starters — security / auth
    "spring-boot-starter-security": "Spring Security",
    "spring-boot-starter-oauth2-client": "OAuth2",
    "spring-boot-starter-oauth2-resource-server": "OAuth2",
    "spring-security-oauth2-jose": "OAuth2",
    # Databases & Drivers
    "postgresql": "PostgreSQL",
    "mysql-connector-j": "MySQL",
    "mysql-connector-java": "MySQL",
    "mongodb-driver-sync": "MongoDB",
    "mongodb-driver-reactivestreams": "MongoDB",
    "neo4j-java-driver": "Neo4j",
    "jedis": "Redis",
    "lettuce-core": "Redis",
    "redisson": "Redis",
    "h2": "H2 Database",
    "elasticsearch-rest-high-level-client": "Elasticsearch",
    "co.elastic.clients:elasticsearch-java": "Elasticsearch",
    # OpenAPI / Swagger
    "springdoc-openapi-starter-webmvc-ui": "OpenAPI / Swagger",
    "springdoc-openapi-starter-webflux-ui": "OpenAPI / Swagger",
    "springfox-swagger2": "OpenAPI / Swagger",
    # JWT
    "jjwt-api": "JWT",
    "jjwt-impl": "JWT",
    "io.jsonwebtoken:jjwt-jackson": "JWT",
    "java-jwt": "JWT",
    # HTTP & serialisation
    "jackson-databind": "Jackson",
    "jackson-core": "Jackson",
    "jackson-module-kotlin": "Jackson",
    "gson": "Gson",
    "okhttp": "OkHttp",
    "httpclient": "Apache HttpClient",
    "httpclient5": "Apache HttpClient",
    # Mapping & Protobuf
    "mapstruct": "MapStruct",
    "protobuf-java": "google",
}

NORM_PY = {
    # Web Frameworks & Servers
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "tornado": "Tornado",
    "uvicorn": "Uvicorn",
    "gunicorn": "Gunicorn",
    # Databases — PostgreSQL
    "psycopg2": "PostgreSQL",
    "psycopg2-binary": "PostgreSQL",
    "psycopg": "PostgreSQL",
    "psycopg-binary": "PostgreSQL",
    "asyncpg": "PostgreSQL",
    # Databases — MySQL
    "pymysql": "MySQL",
    "aiomysql": "MySQL",
    "mysql-connector-python": "MySQL",
    # Databases — MongoDB
    "pymongo": "MongoDB",
    "motor": "MongoDB",
    "beanie": "MongoDB",        # ODM built on motor
    # Databases — Redis
    "redis": "Redis",
    "aioredis": "Redis",
    "redis-py": "Redis",
    # Databases — Graph / Search / Vector
    "neo4j": "Neo4j",
    "qdrant-client": "Qdrant",
    "chromadb": "ChromaDB",
    "pinecone-client": "Pinecone",
    "pinecone": "Pinecone",
    "weaviate-client": "Weaviate",
    # ORMs & query builders
    "sqlalchemy": "SQLAlchemy",
    "sqlmodel": "SQLAlchemy",   # built on SQLAlchemy
    "tortoise-orm": "Tortoise ORM",
    "alembic": "Alembic",
    # Data Science & ML
    "numpy": "NumPy",
    "pandas": "Pandas",
    "polars": "Polars",
    "scipy": "SciPy",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "torch": "PyTorch",
    "pytorch": "PyTorch",
    "torchvision": "PyTorch",
    "torchaudio": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf-keras": "Keras",
    "keras": "Keras",
    "lightgbm": "LightGBM",
    "xgboost": "XGBoost",
    "catboost": "CatBoost",
    "optuna": "Optuna",
    # LLMs, RAG & Agents
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "langchain": "LangChain",
    "langchain-core": "LangChain",
    "langchain-community": "LangChain",
    "langchain-openai": "LangChain",
    "langchain-anthropic": "LangChain",
    "langchain-groq": "LangChain",
    "langchain-mistralai": "LangChain",
    "langchain-google-genai": "LangChain",
    "langchain-chroma": "LangChain",
    "langchain-pinecone": "LangChain",
    "langgraph": "LangGraph",
    "llama-index": "LlamaIndex",
    "llama-index-core": "LlamaIndex",
    "llama-index-llms-openai": "LlamaIndex",
    "transformers": "Hugging Face",
    "huggingface-hub": "Hugging Face",
    "datasets": "Hugging Face",
    "tokenizers": "Hugging Face",
    "diffusers": "Hugging Face",
    "peft": "Hugging Face",
    "trl": "Hugging Face",
    # Google AI
    "google-generativeai": "Google Gemini",
    "google-genai": "Google Gemini",
    "vertexai": "Google Gemini",
    "google-cloud-aiplatform": "Google Gemini",
    # AWS
    "boto3": "AWS SDK",
    "botocore": "AWS SDK",
    "aioboto3": "AWS SDK",
    "aiobotocore": "AWS SDK",
    # Payments & comms
    "stripe": "Stripe",
    # Serialization, validation & tasks
    "pydantic": "Pydantic",
    "pydantic-settings": "Pydantic",
    "pydantic-v1": "Pydantic",
    "celery": "Celery",
    "rq": "RQ",
    "taskiq": "Taskiq",
    # HTTP clients
    "httpx": "HTTPX",
    "requests": "Requests",
    "aiohttp": "Aiohttp",
    "httpcore": "HTTPX",        # httpcore is httpx's transport layer
}

NOISE_JAVA = {
    # Testing
    "junit", "junit-jupiter", "junit-jupiter-api", "junit-jupiter-engine",
    "junit-vintage-engine", "junit-platform-launcher",
    "testng", "mockito-core", "mockito-junit-jupiter", "mockito-inline",
    "assertj-core", "hamcrest", "hamcrest-core", "archunit",
    # Spring dev / test
    "spring-boot-devtools", "spring-boot-starter-test", "spring-security-test",
    "spring-test", "spring-boot-maven-plugin", "spring-restdocs-mockmvc",
    # Build plugins
    "maven-compiler-plugin", "maven-surefire-plugin", "maven-jar-plugin",
    "maven-failsafe-plugin", "maven-resources-plugin", "maven-shade-plugin",
    # Code generation (not a "used library" in the final product)
    "lombok", "lombok-mapstruct-binding", "mapstruct-processor",
    # Logging (infrastructure, not a feature)
    "slf4j-api", "logback-classic", "logback-core",
    "log4j-api", "log4j-core", "log4j-slf4j-impl",
    # Bytecode manipulation
    "byte-buddy", "byte-buddy-agent", "cglib", "asm",
}


NORM_TS = {
    # --- Frontend Frameworks ---
    "react": "React",
    "react-dom": "React",
    # react-router family: all consolidate to React (it's the ecosystem)
    "react-router": "React",
    "react-router-dom": "React",
    "react-router-native": "React",
    # react utility libs that signal React usage
    "react-hook-form": "React",
    "react-icons": "React",
    "react-helmet": "React",
    "react-helmet-async": "React",
    "react-hot-toast": "React",
    "react-toastify": "React",
    "react-dropzone": "React",
    # Next.js and its ecosystem
    "next": "Next.js",
    "next-auth": "Next.js",     # auth layer built for Next.js
    "next-themes": "Next.js",
    "next-i18next": "Next.js",
    # Vue / Nuxt
    "vue": "Vue.js",
    "vue-router": "Vue.js",
    "pinia": "Vue.js",          # official Vue state manager
    "vuex": "Vue.js",
    "nuxt": "Nuxt.js",
    "nuxtjs": "Nuxt.js",        # @nuxtjs/* → "nuxtjs" after clean
    # Svelte / SvelteKit
    "svelte": "Svelte",
    "sveltejs": "SvelteKit",    # @sveltejs/* → "sveltejs" after clean
    # Angular
    "angular": "Angular",       # @angular/* → "angular" after clean
    # Astro
    "astro": "Astro",
    "astrojs": "Astro",
    # --- Backend & Runtimes ---
    "express": "Express",
    "nestjs": "NestJS",         # @nestjs/* → "nestjs" after clean
    "fastify": "Fastify",
    "hookform":"reacthookform",
    "koa": "Koa",
    "hono": "Hono",
    "elysia": "Hono",           # Bun-native, same class
    # --- UI Libraries & Styling ---
    "tailwindcss": "Tailwind CSS",
    "tailwindcss-animate": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "chakra-ui": "Chakra UI",   # @chakra-ui/* → "chakra-ui" after clean
    "mui": "Material UI",       # @mui/* → "mui" after clean
    "shadcn-ui": "ShadCN",
    "shadcn": "ShadCN",
    "radix-ui": "Radix UI",     # @radix-ui/* → "radix-ui" after clean
    "styled-components": "Styled Components",
    "emotion": "Styled Components",   # @emotion/* → "emotion" after clean
    "headlessui": "Tailwind CSS",     # @headlessui/* → always used with Tailwind
    "lucide-react": "Lucide",
    "lucide": "Lucide",
    "gsap": "GSAP",
    "vite": "Vite",
    "vitejs": "Vite",
    # --- State & Data Fetching ---
    "redux": "Redux",
    "reduxjs": "Redux",         # @reduxjs/* → "reduxjs" after clean
    "redux-toolkit": "Redux",
    "zustand": "Zustand",
    "mobx": "MobX",
    "mobx-react-lite": "MobX",
    "tanstack": "React Query",  # @tanstack/* → "tanstack" after clean
    "react-query": "React Query",
    "swr": "SWR",
    # --- Databases & ORMs ---
    "prisma": "Prisma",
    "drizzle-orm": "Drizzle ORM",
    "typeorm": "TypeORM",
    "sequelize": "Sequelize",
    "mongoose": "MongoDB",
    "mongodb": "MongoDB",
    "pg": "PostgreSQL",
    "postgres": "PostgreSQL",
    "@neondatabase": "PostgreSQL",  # Neon serverless postgres
    "mysql2": "MySQL",
    "redis": "Redis",
    "ioredis": "Redis",
    "upstash": "Redis",         # @upstash/* → "upstash" (Redis-over-HTTP)
    "neo4j-driver": "Neo4j",
    # --- GraphQL & RPC ---
    "graphql": "GraphQL",
    "apollo": "Apollo GraphQL", # @apollo/* → "apollo" after clean
    "apollo-server": "Apollo GraphQL",
    "apollo-server-express": "Apollo GraphQL",
    "apollo-client": "Apollo GraphQL",
    "trpc": "tRPC",             # @trpc/* → "trpc" after clean
    # --- Auth ---
    "jsonwebtoken": "JWT",
    "jose": "JWT",
    "bcrypt": "Bcrypt",
    "bcryptjs": "Bcrypt",
    "passport": "Express",      # middleware, signals Express usage
    # --- Utils ---
    "zod": "Zod",
    "yup": "Yup",
    "valibot": "Zod",           # same category as Zod
    "axios": "Axios",
    "socket.io": "Socket.io",
    "socket.io-client": "Socket.io",
    "lodash": "Lodash",
    "lodash-es": "Lodash",
    "date-fns": "React",        # date utility almost always with React
    "dayjs": "React",
}
pkg_to_lang = {
    # Python manifests & lock files
    "pyproject.toml": "py",
    "requirements.txt": "py",
    "Pipfile": "py",
    "Pipfile.lock": "py",
    "poetry.lock": "py",
    "uv.lock": "py",
    "setup.py": "py",
    "setup.cfg": "py",
    # JS/TS manifests & lock files
    "package.json": "ts",
    "package-lock.json": "ts",
    "yarn.lock": "ts",
    "pnpm-lock.yaml": "ts",
    "bun.lockb": "ts",
    # Java / Maven
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
}

NOISE = {"java": NOISE_JAVA, "py": NOISE_PYTHON, "ts": NOISE_TS}
NORM = {"java": NORM_JAVA, "py": NORM_PY, "ts": NORM_TS}



TARGETS = [
                "package.json",
                "pyproject.toml",
                "requirements.txt",
                "pom.xml",
]


HOSTING_BLOCKLIST = {
    "github.com", "gitlab.com", "bitbucket.org",
    "npmjs.com", "npmjs.org", "pypi.org", "pypi.python.org",
    "crates.io", "maven.org", "apache.org"
}


PACKAGE_REGISTRY = {
    "ts": "https://registry.npmjs.org/{pkg}",
    "py": "https://pypi.org/pypi/{pkg}/json",
    "java": "https://search.maven.org/solrsearch/select?q={pkg}&rows=1&wt=json",
}



TO_IGNORE = {
    
}