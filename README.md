# Algorithm Competition RAG Assistant

An intelligent algorithm competition solution based on RAG (Retrieval-Augmented Generation) technology, supporting automatic problem analysis, algorithm recommendation, code generation, and validation.

**Author Contact:** yukaiwu002@gmail.com

---

## ⚠️ Important Notice

**TL;DR: Use `main.py` for algorithm solving. The engineering version is incomplete.**

**This project is currently in development. The engineering version is still under development and cannot be used yet. Please use the original `main.py` file for algorithm problem solving.**

## 🚀 Quick Start

### Using the Original Version (Recommended)

This project is based on a single `main.py` file implementation, containing complete RAG algorithm solving functionality.

#### Environment Setup

1. **Install Python Dependencies**

```bash
pip install -r requirements.txt
```

2. **Start Neo4j Database**

This project uses a pre-configured Neo4j Docker container with complete OI WIKI algorithm data.

**Download Database from Releases**

Due to file size limitations, the Neo4j database file needs to be downloaded separately from GitHub Releases:

```bash
cd neo4j-dump-deploy
scripts/get_dump.sh "https://github.com/Wyk-formal/A-Collaborative-Framework-for-Algorithmic-Problem-Solving/releases/download/v1.0.0/neo4j.dump" neo4j.dump
docker compose up -d
```

**Alternative Download Method:**

If the script doesn't work, you can manually download:

1. Go to the [Releases page](https://github.com/Wyk-formal/A-Collaborative-Framework-for-Algorithmic-Problem-Solving/releases)
2. Download `neo4j.dump` from the latest release
3. Place it in the `neo4j-dump-deploy/dumps/` directory
4. Run `docker compose up -d`

**Access Neo4j:**

- Browser Interface: http://localhost:7474
- Bolt Connection: `bolt://localhost:7687`
- Default Credentials: `neo4j / passcode123` (please change password after first login)
- Neo4j Version: 5.26.10

3. **Configure Environment Variables**

Modify the following configuration in the `main.py` file:

```python
# API Configuration
ZHIPU_API_KEY = "your_zhipu_api_key_here"  # Replace with your ZhipuAI API key

# Neo4j Database Configuration (use default configuration)
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "passcode123"  # Or your modified password
```

#### Usage

Run the `main.py` file:

```bash
python main.py
```

After startup, the program will display two options:

```
Please select mode:
1. Enter problem directly in terminal
2. Read problem from MD document and output to MD document
Please enter your choice (1 or 2):
```

**Mode 1: Interactive Input**

- Enter algorithm problems directly in the terminal
- System will analyze and generate solutions in real-time
- Supports code validation and optimization

**Mode 2: File Processing**

- Write problem content to `input.md` file
- System reads and processes the problem
- Results output to `output.md` file

### Example Usage

#### Interactive Mode Example

```bash
python main.py
# Select mode 1
# Input problem:
# Please implement quicksort algorithm and analyze its time complexity
```

#### File Processing Mode Example

1. Create `input.md` file:

```markdown
# P1001 A+B Problem

## Problem Description

Input two integers a and b, output the value of a+b.

## Input Format

One line, two integers a and b.

## Output Format

One line, the value of a+b.

## Sample Input

1 2

## Sample Output

3
```

2. Run the program:

```bash
python main.py
# Select mode 2
```

3. View results:

The program will generate a complete solution in the `output.md` file, including:

- Problem analysis
- Algorithm approach
- C++ code implementation
- Complexity analysis
- Code validation results

## 📋 Features

### Core Features

- ✅ **Intelligent Problem Analysis**: Automatically parses problem structure and extracts key information
- ✅ **Hybrid Intelligent Retrieval**: Combines full-text, vector, and keyword search
- ✅ **Automatic Code Generation**: Generates complete runnable C++ code
- ✅ **Automatic Validation System**: Compiles and runs code to verify sample correctness
- ✅ **Iterative Optimization**: Automatically fixes code errors
- ✅ **Performance Analysis**: Time and space complexity analysis

### Technical Features

- **RAG Technology**: Combines retrieval and generation for more accurate algorithm recommendations
- **Multi-modal Retrieval**: Supports text, vector, keyword, and other search methods
- **Real-time Validation**: Automatically compiles and runs code to ensure solution correctness
- **Intelligent Optimization**: Automatically improves code based on error information

## 🗄️ Database Information

### Neo4j Graph Database

This project uses Neo4j graph database to store algorithm knowledge base, with data sourced from **OI WIKI**.

**Data Usage Statement:**

- The Neo4j database in this project is built from **OI Wiki** algorithm content.
- **License follows OI Wiki's official notice**: unless otherwise stated, **non-code content** is licensed under **Creative Commons BY-SA 4.0** **with the additional** **The Star And Thank Author License (SATA)**.
- Therefore, when using OI Wiki–derived text and datasets from this repo, you **must**:
  - provide **attribution** (credit OI Wiki and this repository);
  - **share alike** under CC BY-SA 4.0;
  - **add no additional restrictions**;
  - and **Star the OI Wiki GitHub repository** (per the SATA clause).
- The **code** in this repository continues to follow this repository's software license (e.g., MIT) and is separate from CC BY-SA/SATA terms.
- Thanks to the **OI Wiki** community for providing high-quality algorithm resources.

**OI WIKI Citation:**

```bibtex
@misc{oiwiki,
  author = {OI Wiki Team},
  title = {OI Wiki},
  year = {2016},
  publisher = {GitHub},
  journal = {GitHub Repository},
  howpublished = {\url{https://github.com/OI-wiki/OI-wiki}},
}
```

### Database Structure

- **Node Types**: Algorithms, data structures, problem types, etc.
- **Relationship Types**: Algorithm dependencies, similar algorithms, application scenarios, etc.
- **Attribute Information**: Algorithm descriptions, complexity, implementation code, etc.

## 📁 Project Structure

```
├── main.py                    # Main program file (recommended)
├── requirements.txt           # Python dependencies
├── input.md                  # Input file (for mode 2)
├── output.md                 # Output file (for mode 2)
├── answer_*.txt              # Code validation output files
├── neo4j-dump-deploy/        # Neo4j database deployment package
│   ├── docker-compose.yml    # Docker orchestration file
│   ├── dumps/                # Database backup files
│   │   └── neo4j.dump       # OI WIKI algorithm data backup
│   ├── scripts/              # Deployment scripts
│   │   ├── get_dump.sh      # Database download script
│   │   └── load_dump.sh     # Database loading script
│   ├── Makefile             # Convenient commands
│   └── README.md            # Database deployment documentation
├── src/                      # Engineering version source code (under development)
├── web/                      # Web interface (under development)
├── cli/                      # Command line interface (under development)
└── README.md                 # Project documentation
```

## ⚙️ Environment Requirements

### System Requirements

- **Python**: 3.8+
- **Docker**: 20.0+ (for Neo4j database deployment)
- **Docker Compose**: 2.0+ (for container orchestration)
- **Compiler**: g++ or clang++ (for code validation)
- **Operating System**: Windows, macOS, Linux

### Dependencies

Main dependency versions (based on chatbot virtual environment):

```
zhipuai==2.1.5.20250801
neo4j==5.28.2
numpy==2.2.6
psutil==7.0.0
Flask==3.1.2
Flask-SocketIO==5.5.1
eventlet==0.40.3
```

**Note**: Python neo4j driver is compatible with 5.x server minor versions, exact version match is not required.

For complete dependency list, please refer to the `requirements.txt` file.

## 🔧 Configuration

### API Configuration

Configure ZhipuAI API in `main.py`:

```python
ZHIPU_API_KEY = "your_api_key_here"
EMBEDDING_MODEL = "embedding-2"
CHAT_MODEL = "glm-4.5"
```

### Database Configuration

```python
import os
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "passcode123")
NEO4J_DATABASE = "neo4j"
```

**Note**: You can override the password by setting environment variable: `NEO4J_PASSWORD=your_password python main.py`

### Debug Configuration

```python
SHOW_DEBUG_INFO = False      # Control debug information display
SHOW_QUERY_WARNINGS = False  # Control database query warnings
```

## 🚧 Engineering Version Status

**Note: The engineering version is still under development with incomplete functionality. Not recommended for use.**

The engineering version includes the following modules (under development):

- `src/` - Modular source code
- `web/` - Web visualization interface
- `cli/` - Command line tools
- `docker/` - Containerized deployment

**Current Status:**

- ❌ Web Interface: Partially functional but has stability issues
- ❌ CLI Tools: Incomplete interface
- ❌ Modular Code: Some modules missing
- ❌ Docker Deployment: Incomplete configuration

**Recommendations:**

- Use the original `main.py` file for algorithm solving
- Wait for the engineering version to be completed before using new features

## 🗄️ Neo4j Database Management

### Database Deployment

This project uses a Docker containerized Neo4j database with complete OI WIKI algorithm data.

#### Quick Start

```bash
# Enter database deployment directory
cd neo4j-dump-deploy

# Download database from releases (first time only)
scripts/get_dump.sh "https://github.com/Wyk-formal/A-Collaborative-Framework-for-Algorithmic-Problem-Solving/releases/download/v1.0.0/neo4j.dump" neo4j.dump

# Start database
docker compose up -d

# Optional: Override NEO4J_AUTH via .env file
# Create .env in neo4j-dump-deploy/ with: NEO4J_AUTH=neo4j/your_password
# Then run: docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

#### Database Management Commands

```bash
# Stop database
cd neo4j-dump-deploy
make down

# Restart database
make down && make up

# Clean data (use with caution)
make clean

# View logs
make logs
```

#### Database Access

- **Web Interface**: http://localhost:7474
- **Bolt Connection**: `bolt://localhost:7687`
- **Default Credentials**: `neo4j / passcode123`
- **Database Version**: Neo4j 5.26.10

#### Data Validation

After startup, you can validate data through the following methods:

```bash
# Check container status
docker compose ps

# View data loading logs
# macOS/Linux:
docker compose logs neo4j -f --tail=200 | grep -m1 "Load OK"
# Windows (PowerShell):
docker compose logs neo4j -f --tail=200 | findstr "Load OK"

# Access through browser at http://localhost:7474
# Login with default credentials and check data node count
```

### Data Backup and Recovery

```bash
# Create data backup (Neo4j 5.x, OFFLINE)
cd neo4j-dump-deploy

# 1) Stop service to ensure offline operation
docker compose down

# 2) Use one-time container for offline export (mount data/logs/dumps)
docker run --rm \
  -v "$PWD/neo4j/data:/data" \
  -v "$PWD/neo4j/logs:/logs" \
  -v "$PWD/dumps:/out" \
  neo4j:5.26.10 \
  bash -lc '/var/lib/neo4j/bin/neo4j-admin database dump neo4j --to-path=/out --overwrite-destination'
# Backup is now at ./dumps/neo4j.dump

# 3) Restart service if needed
docker compose up -d


# Restore from backup (OFFLINE)
cd neo4j-dump-deploy

# 1) Stop service to ensure offline operation
docker compose down

# 2) Use one-time container for offline restore (load from ./dumps/)
docker run --rm \
  -v "$PWD/neo4j/data:/data" \
  -v "$PWD/neo4j/logs:/logs" \
  -v "$PWD/dumps:/imports" \
  neo4j:5.26.10 \
  bash -lc '/var/lib/neo4j/bin/neo4j-admin database load neo4j --from-path=/imports --overwrite-destination'

# 3) Start service
docker compose up -d
```

**Alternative for simple restore**: If you only want to use the built-in auto-import script, the process is simpler: place `neo4j.dump` in `neo4j-dump-deploy/dumps/`, then run `make clean && docker compose up -d` (first startup will auto-load, subsequent starts will skip).

**Note**: The "offline one-time container" approach above is suitable for precise controllable backup/restore operations and avoids the risk of executing admin commands on running instances.

## 🔍 Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**

   ```
   Solutions:
   - Check if Docker service is running: docker --version
   - Check Neo4j container status: cd neo4j-dump-deploy && docker compose ps
   - View container logs: cd neo4j-dump-deploy && docker compose logs
   - Confirm port is not occupied:
     # macOS/Linux:
     lsof -i :7687
     # Windows (PowerShell):
     Get-Process -Id (Get-NetTCPConnection -LocalPort 7687).OwningProcess
   ```

2. **Neo4j Database Loading Failed**

   ```
   Solutions:
   - Check if dump file exists: ls neo4j-dump-deploy/dumps/
   - Reload database: cd neo4j-dump-deploy && make clean && docker compose up -d
   - Check if disk space is sufficient
   ```

3. **API Call Failed**

   ```
   Solution: Check if ZHIPU_API_KEY is correct and network connection is normal
   ```

4. **Code Compilation Failed**

   ```
   Solution: Ensure g++ or clang++ compiler is installed on the system
   ```

5. **Dependency Installation Failed**

   ```
   Solution: Use conda or pip to install packages in requirements.txt
   ```

6. **Docker File Sharing Issues (macOS)**
   ```
   Solution: If Docker cannot read/write ./dumps or ./neo4j/data directories,
   go to Docker Desktop → Settings → Resources → File Sharing and add this project path.
   ```

### Debug Mode

Set in `main.py`:

```python
SHOW_DEBUG_INFO = True  # Show detailed debug information
```

## 📊 Performance Information

### Processing Capabilities

- **Problem Analysis**: Supports various algorithm competition problem formats
- **Code Generation**: Generates standard C++ code
- **Validation Speed**: Single problem processing time approximately 30-60 seconds
- **Accuracy**: Based on RAG technology, provides high-accuracy algorithm recommendations

### Resource Consumption

- **Memory Usage**: Approximately 200-500MB
- **CPU Usage**: Single core, high usage during processing
- **Network Traffic**: Depends on API calls, requires stable network

## 🤝 Contributing

Contributions are welcome!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2024 Algorithm RAG Assistant

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🙏 Acknowledgments

- [ZhipuAI](https://www.zhipuai.cn/) - Providing powerful AI capabilities
- [Neo4j](https://neo4j.com/) - Graph database support
- [OI WIKI](https://oi-wiki.org/) - Algorithm knowledge base data source
- All contributors and users

## 📞 Support

For questions or suggestions, please:

1. Check the troubleshooting section in this documentation
2. Submit an [Issue](https://github.com/your-repo/issues)
3. Contact the maintainer

---

**Algorithm Competition RAG Assistant** - Making algorithm learning smarter!

> **Important Reminder**: Please use the `main.py` file for algorithm solving. The engineering version is still under development.
