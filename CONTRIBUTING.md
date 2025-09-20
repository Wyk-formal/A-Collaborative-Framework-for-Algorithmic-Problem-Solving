# Contributing to Algorithm Competition RAG Assistant

Thank you for your interest in contributing to this project! This document provides guidelines for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributions from everyone.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/chatbot.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit your changes: `git commit -m 'Add some feature'`
7. Push to your branch: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Neo4j (via Docker)
- ZhipuAI API key

### Installation

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set up Neo4j database:

   ```bash
   cd neo4j-dump-deploy
   docker compose up -d
   ```

3. Configure API keys:
   ```bash
   # Edit main.py or use environment variables
   export ZHIPU_API_KEY="your_api_key"
   ```

## Project Structure

```
├── main.py                    # Original single-file implementation (stable)
├── src/                      # Modular implementation (under development)
├── web/                      # Web interface (under development)
├── cli/                      # Command line interface (under development)
├── neo4j-dump-deploy/        # Database deployment
└── requirements.txt          # Dependencies
```

## Contributing Guidelines

### Areas for Contribution

1. **Algorithm Knowledge Base**: Add more algorithm examples and explanations
2. **Code Validation**: Improve C++ code compilation and testing
3. **Web Interface**: Enhance the user interface and experience
4. **Documentation**: Improve documentation and examples
5. **Testing**: Add test cases and improve reliability
6. **Performance**: Optimize search and generation performance

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings for functions and classes
- Include type hints where appropriate
- Add comments for complex logic

### Testing

- Test your changes with the original `main.py` functionality
- Ensure backward compatibility
- Test with various algorithm problems
- Verify code compilation and execution works

### Documentation

- Update README.md if needed
- Add docstrings to new functions
- Include examples for new features
- Update configuration documentation

## Pull Request Process

1. **Description**: Provide a clear description of your changes
2. **Testing**: Include information about testing performed
3. **Documentation**: Update documentation as needed
4. **Backward Compatibility**: Ensure original functionality is preserved
5. **Review**: Be responsive to feedback during review

## Reporting Issues

When reporting issues, please include:

1. **Environment**: Python version, OS, Docker version
2. **Steps to Reproduce**: Clear steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Error Messages**: Any error messages or logs
6. **Configuration**: Relevant configuration details (without sensitive data)

## Feature Requests

When requesting features:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: Suggest how the feature might work
3. **Alternatives**: Mention any alternative solutions considered
4. **Additional Context**: Any other relevant information

## Development Priorities

Current development priorities:

1. **Stability**: Maintain and improve the original `main.py` functionality
2. **Web Interface**: Complete the web interface implementation
3. **Documentation**: Improve user and developer documentation
4. **Testing**: Add comprehensive test coverage
5. **Performance**: Optimize search and generation performance

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, please:

1. Check existing issues and documentation
2. Open a new issue with the "question" label
3. Contact the maintainers

Thank you for contributing!
