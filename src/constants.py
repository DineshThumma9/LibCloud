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
    "H2 Database": "h2database",
    "OpenAPI / Swagger": "swagger",
    "JWT": "jsonwebtokens",
    "Jackson": "spring",
    "Gson": "google",
    "OkHttp": "okta",
    "Apache HttpClient": "apache",
    "MapStruct": "mapstruct",
    "Apache Kafka": "apachekafka",
    "gRPC": "grpc",
    "Docker": "docker",
    # Python — web
    "FastAPI": "fastapi",
    "Flask": "flask",
    "Django": "django",
    "Starlette": "starlette",
    "Tornado": "tornado",
    "Uvicorn": "uvicorn",
    "Gunicorn": "gunicorn",
    "Jinja": "jinja",
    "Jinja2": "jinja",
    "Git": "git",
    # Python — data / ML
    "SQLAlchemy": "sqlalchemy",
    "Tortoise ORM": "python",
    "Alembic": "alembic",
    "Qdrant": "qdrant",
    "ChromaDB": "chroma",
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
    "Mistral": "mistral",
    "LangChain": "langchain",
    "LangGraph": "langchain",
    "LlamaIndex": "llama-index",
    "Hugging Face": "huggingface",
    "Pydantic": "pydantic",
    "Celery": "celery",
    "RQ": "python",
    "Taskiq": "taskiq",
    "Sentry": "sentry",
    "PostHog": "posthog",
    "HTTPX": "httpx",
    "Requests": "pypi",
    "Aiohttp": "aiohttp",
    "AWS SDK": "amazonwebservices",
    "Stripe": "stripe",
    "Firebase": "firebase",
    "Google": "google",
    "Google Cloud": "googlecloud",
    "Google Gemini": "googlegemini",
    "Oracle": "oracle",
    "SonarQube": "sonarqube",
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
    # CI/CD & Cloud
    "GitHub Actions": "githubactions",
    "Azure": "azure",
    "Microsoft Azure": "azure",
    # Java Testing & Dev
    "JUnit": "junit5",
    "REST-Assured": "rest-assured",
    "Lombok": "lombok",
    # Search & LLMs
    "DuckDuckGo": "duckduckgo",
    "Gemini": "googlegemini",
    "Google Gemini": "googlegemini",
    "Vercel AI SDK": "vercel",
    "ai": "vercel",
    # Testing & QA
    "Playwright": "playwright",
    "Pytest": "pytest",
    "Jest": "jest",
    "Vitest": "vitest",
    "Cypress": "cypress",
    # Linters & Formatters
    "Ruff": "ruff",
    "ESLint": "eslint",
    "Prettier": "prettier",
    "Black": "python",
    "Flake8": "python",
    "Mypy": "python",
    "Pylint": "python",
    "isort": "python",
    # Go
    "Gin": "gin",
    "Fiber": "gofiber",
    "GORM": "gorm",
    "Go": "go",
    # Rust
    "Tokio": "tokio",
    "Actix": "actix",
    "Tauri": "tauri",
    "Yew": "yew",
    "Rust": "rust",
    # Ruby
    "Ruby on Rails": "rubyonrails",
    "Sinatra": "sinatra",
    "Sidekiq": "sidekiq",
    "RSpec": "rspec",
    "Ruby": "ruby",
    "RuboCop": "rubocop",
    # Kotlin
    "Ktor": "ktor",
    "Kotlin": "kotlin",
    "Retrofit": "square",
}


clean_pkg = {
    "ts": lambda x: x.split("/")[0].strip("@"),
    "java": lambda x: x.split(":")[-1],
    "kotlin": lambda x: x.split(":")[-1],
    "actions": lambda x: x.split("@")[0].strip(),
    "py": lambda x: re.sub(r'\[.*\]', '', x).strip(),
    "go": lambda x: x.split("/")[-1],
    "rust": lambda x: x.strip(),
    "ruby": lambda x: x.strip(),
}




NOISE_PYTHON = {
    # Testing & mocking utilities
    "hypothesis", "tox", "nox", "factory-boy",
    "faker", "freezegun", "respx", "responses", "httpretty", "vcrpy",
    # Security checkers
    "bandit", "safety", "semgrep",
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
    ".idea",  # IDE artifact
    "click",  # CLI helper, rarely the "point" of a project
 "colorama",  # terminal styling
    "python-dotenv", "environs",  # env var loaders
    "tqdm",  # progress bars
    "h11", "httplib2", "oauthlib", "proto-plus", 
    "pyasn1", "pyasn1_modules", "pyparsing", "annotated-types", "annotated-doc",
    # Low-level serialization, parsing & type helpers
    "typing-inspection", "typing_extensions", "eval-type-backport", "tzdata", "pytz", "python-dateutil",
    "markupsafe", "jiter", "orjson", "ormsgpack", "flatbuffers", "fastavro",
    "jsonschema", "jsonschema-specifications", "jsonpointer", "jsonpatch", "dirtyjson",
    "tenacity", "backoff", "aiolimiter", "aiohappyeyeballs", "httptools", "hpack", "hyperframe",
    "humanfriendly", "coloredlogs", "click-didyoumean", "click-plugins", "click-repl",
    "billiard", "amqp", "kombu", "fsspec", "blobfile", "filetype", "smmap",
    "importlib-metadata", "importlib-resources", "email-validator", "uritemplate",
    "rpds-py", "xxhash", "zstandard", "cffi", "ecdsa", "rsa", "distro", "pyyml", "defusedxml",
    "soupsieve", "dataclasses-json", "dataclasses_json", "durationpy",
    # Google transport & auth plumbing
    "google-auth", "google-auth-httplib2", "google-auth-oauthlib",
    "google-api-core", "googleapis-common-protos",
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
    # Compilers & type checkers
    "typescript", "ts-node", "tsx", "tsc-alias",
    # Build tools & bundlers
    "esbuild", "rollup", "webpack", "webpack-cli", "webpack-dev-server",
    "swc",                      # @swc/* → "swc" after clean
    "babel",                    # @babel/* → "babel" after clean
    "@babel/core", "@babel/preset-env", "@babel/preset-react", "@babel/preset-typescript",
    # CSS tooling & micro-utilities
    "postcss", "autoprefixer",
    "clsx", "class-variance-authority", "tailwind-merge", "globals",
    "tw-animate-css", "fontsource-variable", "oxlint", "next-themes", "emotion",
    # Dev utilities
    "nodemon", "ts-node-dev", "concurrently", "rimraf", "cross-env",
    "dotenv", "dotenv-cli", "env-cmd",
    "npm-check-updates", "patch-package", "madge", "use-stick-to-bottom", "tokenlens",
    "eventsource-parser", "lru-cache", "nanoid", "ms",
    # Excluded library with duplicate branding
    "streamdown",
    # Runtime shims / low-level
    "tslib", "core-js", "object-assign",
    # Storybook
    "storybook",                # @storybook/* → "storybook" after clean
}

NOISE_JS = {
    # Testing shims
    "puppeteer", "jasmine",
    # Babel
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
    "jjwt-jackson": "JWT",
    "io.jsonwebtoken:jjwt-jackson": "JWT",
    "java-jwt": "JWT",
    # gRPC & Protobuf
    "grpc-protobuf": "gRPC",
    "grpc-netty-shaded": "gRPC",
    "grpc-spring-boot-starter": "gRPC",
    "grpc-stub": "gRPC",
    "protobuf-maven-plugin": "Google",
    "firebase-admin": "Google",
    # Spring extras
    "spring-boot-starter": "Spring Boot",
    "spring-boot-starter-graphql": "Spring Boot",
    "spring-graphql-test": "Spring Boot",
    "spring-cloud-starter-gateway": "Spring Boot",
    "spring-cloud-dependencies": "Spring Boot",
    "spring-kafka-test": "Apache Kafka",
    "aws-cdk-lib": "AWS SDK",
    "aws-java-sdk": "AWS SDK",
    "ojdbc11": "Oracle",
    "sonar-maven-plugin": "SonarQube",
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
    "mapstruct-processor": "MapStruct",
    "lombok": "Lombok",
    "lombok-mapstruct-binding": "Lombok",
    "protobuf-java": "Google",
    # Testing
    "junit": "JUnit",
    "junit-jupiter": "JUnit",
    "junit-jupiter-api": "JUnit",
    "junit-jupiter-engine": "JUnit",
    "junit-vintage-engine": "JUnit",
    "junit-platform-launcher": "JUnit",
    "rest-assured": "REST-Assured",
}

NORM_PY = {
    # Web Frameworks & Servers
    "fastapi": "FastAPI",
    "fastapi-cli": "FastAPI",
    "python-multipart": "FastAPI",
    "httpx-sse": "HTTPX",
    "flask": "Flask",
    "flask-wtf": "Flask",
    "flask-login": "Flask",
    "flask-mail": "Flask",
    "flask-bcrypt": "Flask",
    "flask-sqlalchemy": "Flask",
    "fastapi-mail":"FastAPI",

    "wtforms": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "tornado": "Tornado",
    "uvicorn": "Uvicorn",
    "gunicorn": "Gunicorn",
    "jinja2": "Jinja",
    "jinja": "Jinja",
    "docker": "Docker",
    "docker-compose": "Docker",
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
    "langchain-openai": "OpenAI",
    "langchain-anthropic": "Anthropic",
    "langchain-groq": "Groq",
    "langchain-mistralai": "Mistral",
    "mistralai": "Mistral",
    "langchain-google-genai": "Gemini",
    "langchain-chroma": "ChromaDB",
    "langchain-pinecone": "Pinecone",
    "langsmith": "LangChain",
    "langchain-huggingface": "Hugging Face",
    "langchain-gemini": "Gemini",
    "langchain-text-splitters": "LangChain",
    "langgraph": "LangGraph",
    "langgraph-checkpoint-sqlite": "SQLite",
    "langgraph-sdk": "LangGraph",
    "langgraph-prebuilt": "LangGraph",
    "langgraph-checkpoint": "LangGraph",
    "llama-index": "LlamaIndex",
    "llama-index-core": "LlamaIndex",
    "llama-index-llms-openai": "OpenAI",
    "llama-cloud": "LlamaIndex",
    "llama-index-cli": "LlamaIndex",
    "llama-cloud-services": "LlamaIndex",
    "transformers": "Hugging Face",
    "huggingface-hub": "Hugging Face",
    "datasets": "Hugging Face",
    "tokenizers": "Hugging Face",
    "diffusers": "Hugging Face",
    "peft": "Hugging Face",
    "trl": "Hugging Face",
    # Google AI & Cloud / APIs
    "google-generativeai": "Gemini",
    "google-genai": "Gemini",
    "vertexai": "Gemini",
    "google-cloud-aiplatform": "Gemini",
    "google-api-python-client": "Google",
    "google-cloud-storage": "Google Cloud",
    "google-cloud-core": "Google Cloud",
    "axois": "Axios",
    # AWS
    "boto3": "AWS SDK",
    "botocore": "AWS SDK",
    "aioboto3": "AWS SDK",
    "langchain-neo4j":"neo4j",
    "aiobotocore": "AWS SDK",
    # Payments & comms
    "stripe": "Stripe",
    # Serialization, validation & tasks
    "pydantic": "Pydantic",
    "pydantic_core": "Pydantic",
    "pydantic-core": "Pydantic",
    "pydantic-settings": "Pydantic",
    "pydantic-v1": "Pydantic",
    "gitpython": "Git",
    "gitdb": "Git",
    "git-filter-repo": "Git",
    "grpcio": "gRPC",
    "grpcio-status": "gRPC",
    "celery": "Celery",
    "celery-types": "Celery",
    "rq": "RQ",
    "taskiq": "Taskiq",
    "taskiq-redis": "Taskiq",
    "taskiq-fastapi": "Taskiq",
    "taskiq-aio-pika": "Taskiq",
    "sentry-sdk": "Sentry",
    "sentry": "Sentry",
    "posthog": "PostHog",
    "falkordb": "FalkorDB",
    "langchain-falkordb": "FalkorDB",
    "litellm": "LiteLLM",
    # HTTP clients
    "httpx": "HTTPX",
    "requests": "Requests",
    "aiohttp": "Aiohttp",
    "httpcore": "HTTPX",        # httpcore is httpx's transport layer
    "google-ai-generativelanguage": "Gemini",
    "ddgs": "DuckDuckGo",
    "duckduckgo-search": "DuckDuckGo",
    # Testing & QA
    "pytest": "Pytest",
    "pytest-cov": "Pytest",
    "pytest-asyncio": "Pytest",
    "pytest-mock": "Pytest",
    "pytest-xdist": "Pytest",
    "pytest-env": "Pytest",
    "pytest-timeout": "Pytest",
    "pytest-benchmark": "Pytest",
    "pytest-randomly": "Pytest",
    "playwright": "Playwright",
    # Linters & Formatters
    "ruff": "Ruff",
    "black": "Black",
    "flake8": "Flake8",
    "mypy": "Mypy",
    "pylint": "Pylint",
    "isort": "isort",
}

NOISE_JAVA = {
    # Testing & mocking
    "testng", "mockito-core", "mockito-junit-jupiter", "mockito-inline",
    "assertj-core", "hamcrest", "hamcrest-core", "archunit",
    # Spring dev / test
    "spring-boot-devtools", "spring-boot-starter-test", "spring-security-test",
    "spring-test", "spring-boot-maven-plugin", "spring-restdocs-mockmvc",
    # Build plugins
    "maven-compiler-plugin", "maven-surefire-plugin", "maven-jar-plugin",
    "maven-failsafe-plugin", "maven-resources-plugin", "maven-shade-plugin",
    # Logging (infrastructure, not a feature)
    "slf4j-api", "logback-classic", "logback-core",
    "log4j-api", "log4j-core", "log4j-slf4j-impl",
    # Bytecode manipulation
    "byte-buddy", "byte-buddy-agent", "cglib", "asm",
    # Test & runtime utilities
    "annotations-api", "javafaker", "reactor-test",
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
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "tailwindcss-animate": "Tailwind CSS",
    "ai": "Vercel AI SDK",
    "bootstrap": "Bootstrap",
    "chakra-ui": "Chakra UI",   # @chakra-ui/* → "chakra-ui" after clean
    "mui": "Material UI",       # @mui/* → "mui" after clean
    "shadcn-ui": "ShadCN",
    "shadcn": "ShadCN",
    "cmdk": "ShadCN",
    "sonner": "React",
    "react-responsive": "React",
    "react-infinite-scroll-component": "React",
    "dockerode": "Docker",
    "radix-ui": "Radix UI",     # @radix-ui/* → "radix-ui" after clean
    "styled-components": "Styled Components",   # @emotion/* → "emotion" after clean
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
    "axois": "Axios",
    "socket.io": "Socket.io",
    "socket.io-client": "Socket.io",
    "lodash": "Lodash",
    "lodash-es": "Lodash",
    "date-fns": "React",        # date utility almost always with React
    "dayjs": "React",
    # --- Monitoring & Analytics ---
    "sentry": "Sentry",
    "@sentry": "Sentry",
    "posthog": "PostHog",
    "@posthog": "PostHog",
    # --- Markdown & Content ---
    "remark": "Remark",
    "remark-parse": "Remark",
    "remark-stringify": "Remark",
    "remark-gfm": "Remark",
    "remark-math": "Remark",
    "remark-breaks": "Remark",
    "remark-html": "Remark",
    "remark-rehype": "Remark",
    "rehype": "Remark",
    "rehype-highlight": "Remark",
    "rehype-katex": "Remark",
    "rehype-mathjax": "Remark",
    "rehype-stringify": "Remark",
    "rehype-raw": "Remark",
    "react-markdown": "Remark",
    "unified": "Remark",
    # --- Testing & QA ---
    "playwright": "Playwright",
    "jest": "Jest",
    "ts-jest": "Jest",
    "vitest": "Vitest",
    "cypress": "Cypress",
    # --- Linters & Formatters ---
    "eslint": "ESLint",
    "eslint-plugin-react-hooks": "ESLint",
    "eslint-plugin-react-refresh": "ESLint",
    "vite-plugin-eslint": "ESLint",
    "typescript-eslint": "ESLint",
    "prettier": "Prettier",
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
    # Kotlin
    "build.gradle.kts": "kotlin",
    # Go
    "go.mod": "go",
    "go.sum": "go",
    # Rust
    "Cargo.toml": "rust",
    "Cargo.lock": "rust",
    # Ruby
    "Gemfile": "ruby",
    "Gemfile.lock": "ruby",
}

# --- Go Normalization ---
NORM_GO = {
    "gin": "Gin",
    "gin-gonic": "Gin",
    "fiber": "Fiber",
    "echo": "Echo",
    "chi": "Chi",
    "gorilla": "Gorilla",
    "mux": "Gorilla",
    "zap": "Zap",
    "logrus": "Logrus",
    "zerolog": "Zerolog",
    "gorm": "GORM",
    "sqlx": "SQLx",
    "pq": "PostgreSQL",
    "pgx": "PostgreSQL",
    "go-sql-driver": "MySQL",
    "testify": "Testify",
    "cobra": "Cobra",
    "viper": "Viper",
    "grpc": "gRPC",
    "protobuf": "Protocol Buffers",
    "redis": "Redis",
    "go-redis": "Redis",
    "mongo-go-driver": "MongoDB",
    "kafka-go": "Kafka",
    "sarama": "Kafka",
}

NOISE_GO = {
    "xerrors", "sync", "crypto", "net", "sys", "text", "tools",
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

# --- Rust Normalization ---
NORM_RUST = {
    "tokio": "Tokio",
    "async-std": "Async-std",
    "actix": "Actix",
    "actix-web": "Actix",
    "axum": "Axum",
    "rocket": "Rocket",
    "warp": "Warp",
    "serde": "Serde",
    "serde_json": "Serde",
    "diesel": "Diesel",
    "sqlx": "SQLx",
    "sea-orm": "SeaORM",
    "rusqlite": "SQLite",
    "postgres": "PostgreSQL",
    "redis": "Redis",
    "tauri": "Tauri",
    "yew": "Yew",
    "clap": "Clap",
    "tracing": "Tracing",
    "log": "Log",
    "env_logger": "Env Logger",
    "reqwest": "Reqwest",
    "hyper": "Hyper",
    "anyhow": "Anyhow",
    "thiserror": "Thiserror",
    "rand": "Rand",
    "regex": "Regex",
    "rayon": "Rayon",
    "crossbeam": "Crossbeam",
    "tonic": "gRPC",
    "prost": "Protocol Buffers",
    "criterion": "Criterion",
}

NOISE_RUST = {
    "cfg-if", "bitflags", "lazy_static", "once_cell",
}

# --- Ruby Normalization ---
NORM_RUBY = {
    "rails": "Ruby on Rails",
    "railties": "Ruby on Rails",
    "activerecord": "Ruby on Rails",
    "actionpack": "Ruby on Rails",
    "sinatra": "Sinatra",
    "hanami": "Hanami",
    "sidekiq": "Sidekiq",
    "resque": "Resque",
    "delayed_job": "Delayed Job",
    "rspec": "RSpec",
    "rspec-rails": "RSpec",
    "minitest": "Minitest",
    "capybara": "Capybara",
    "cucumber": "Cucumber",
    "puma": "Puma",
    "unicorn": "Unicorn",
    "passenger": "Passenger",
    "devise": "Devise",
    "cancancan": "CanCanCan",
    "pundit": "Pundit",
    "pg": "PostgreSQL",
    "mysql2": "MySQL",
    "sqlite3": "SQLite",
    "redis": "Redis",
    "faraday": "Faraday",
    "httparty": "HTTParty",
    "rubocop": "RuboCop",
}

NOISE_RUBY = {
    "bundler", "rake", "bootsnap", "zeitwerk",
}

# --- Kotlin Normalization ---
NORM_KOTLIN = {
    "ktor": "Ktor",
    "ktor-server-core": "Ktor",
    "ktor-server-netty": "Ktor",
    "ktor-client-core": "Ktor",
    "ktor-client-cio": "Ktor",
    "kotlinx-coroutines-core": "Kotlin",
    "kotlinx-coroutines-android": "Kotlin",
    "kotlinx-coroutines-reactive": "Kotlin",
    "kotlinx-coroutines-reactor": "Kotlin",
    "kotlinx-coroutines-test": "Kotlin",
    "kotlinx-serialization-json": "Kotlin",
    "firebase-auth-ktx": "Firebase",
    "firebase-messaging-ktx": "Firebase",
    "firebase-firestore-ktx": "Firebase",
    "firebase-analytics-ktx": "Firebase",
    "firebase-common-ktx": "Firebase",
    "exposed-core": "Exposed",
    "exposed-dao": "Exposed",
    "exposed-jdbc": "Exposed",
    "spring-boot-starter-web": "Spring Boot",
    "spring-boot-starter-data-jpa": "Spring Boot",
    "retrofit": "Retrofit",
    "okhttp": "OkHttp",
    "moshi": "Moshi",
    "arrow-core": "Arrow",
    "mockk": "MockK",
    "kotest": "Kotest",
}

NOISE_KOTLIN = {
    "kotlin-stdlib", "kotlin-stdlib-jdk8", "kotlin-stdlib-jdk7", "kotlin-stdlib-common",
    "kotlin-reflect", "kotlin-test", "kotlin-test-junit", "kotlin-test-junit5",
    "spring-security-test", "spring-boot-starter-test", "reactor-test",
}

NORM_ACTIONS = {
    # GitHub Actions
    "actions/checkout": "GitHub Actions",
    "actions/setup-node": "GitHub Actions",
    "actions/setup-python": "GitHub Actions",
    "actions/setup-java": "GitHub Actions",
    "actions/setup-go": "GitHub Actions",
    "actions/cache": "GitHub Actions",
    "actions/upload-artifact": "GitHub Actions",
    "actions/download-artifact": "GitHub Actions",
    "actions/github-script": "GitHub Actions",
    "actions/stale": "GitHub Actions",
    "actions/labeler": "GitHub Actions",
    # Docker Actions
    "docker/build-push-action": "Docker",
    "docker/login-action": "Docker",
    "docker/setup-buildx-action": "Docker",
    "docker/setup-qemu-action": "Docker",
    "docker/metadata-action": "Docker",
    # Azure Actions
    "azure/webapps-deploy": "Azure",
    "azure/login": "Azure",
    "azure/cli": "Azure",
    "azure/docker-login": "Azure",
    "azure/appservice-build": "Azure",
    "azure/k8s-deploy": "Azure",
    "azure/k8s-set-context": "Azure",
}

NOISE_ACTIONS: set[str] = set()

NOISE = {
    "java": NOISE_JAVA,
    "py": NOISE_PYTHON,
    "ts": NOISE_TS,
    "actions": NOISE_ACTIONS,
    "kotlin": NOISE_KOTLIN,
    "go": NOISE_GO,
    "rust": NOISE_RUST,
    "ruby": NOISE_RUBY,
}

NORM = {
    "java": NORM_JAVA,
    "py": NORM_PY,
    "ts": NORM_TS,
    "actions": NORM_ACTIONS,
    "kotlin": NORM_KOTLIN,
    "go": NORM_GO,
    "rust": NORM_RUST,
    "ruby": NORM_RUBY,
}



TARGETS = [
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "Dockerfile",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yaml",
]


HOSTING_BLOCKLIST = {
    "github.com", "gitlab.com", "bitbucket.org",
    "npmjs.com", "npmjs.org", "pypi.org", "pypi.python.org",
    "crates.io", "maven.org", "apache.org", "rubygems.org", "proxy.golang.org"
}


PACKAGE_REGISTRY = {
    "ts": "https://registry.npmjs.org/{pkg}",
    "py": "https://pypi.org/pypi/{pkg}/json",
    "java": "https://search.maven.org/solrsearch/select?q={pkg}&rows=1&wt=json",
    "kotlin": "https://search.maven.org/solrsearch/select?q={pkg}&rows=1&wt=json",
    "rust": "https://crates.io/api/v1/crates/{pkg}",
    "ruby": "https://rubygems.org/api/v1/gems/{pkg}.json",
}



TO_IGNORE = {
    
}