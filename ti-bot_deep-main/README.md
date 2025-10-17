# TI-Bot Deep: AI Assistant Pipeline

A complete implementation of an intelligent AI assistant system that helps users with technical questions, troubleshooting, and information retrieval across various enterprise tools and knowledge bases.

## 🎯 What is TI-Bot Deep?

TI-Bot Deep is an updated AI assistant that include  context, remembers conversations, and provides responses by combining multiple AI technologies:

- **Knowledge Base Search**: Finds relevant information from documentation and previous conversations
- **Memory System**: Remembers what you've discussed across sessions
- **Multi-Agent Processing**: Uses specialized AI agents for different types of questions
- **Enterprise Integration**: Connects to tools like Jira, GitLab, Confluence, and more

## � How It Works

### Simple User Flow
1. **Ask a Question**: You send a message to TI-Bot
2. **Context Understanding**: The system analyzes your question and recalls relevant past conversations
3. **Smart Search**: Searches through knowledge bases, documentation, and enterprise tools
4. **Intelligent Response**: Combines information and provides a helpful, contextual answer
5. **Memory Storage**: Saves the conversation for future reference

### Key Components

**Knowledge Base Service (Hades)**
- Stores and searches through technical documentation
- Uses advanced text processing to understand content
- Provides relevant information based on your questions

**AI Agent Service (Zion)**
- Manages conversations and maintains context
- Coordinates between different tools and data sources
- Generates intelligent responses using large language models

**Memory System**
- Remembers conversations across sessions
- Learns from interactions to improve responses
- Maintains user preferences and context

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- Docker (for easy setup)
- Basic terminal/command line knowledge

### Quick Setup
```bash
# Navigate to the project directory
cd ti-bot_deep

# Start the system with Docker
docker-compose up -d

# The AI assistant will be available at:
# - Main service: http://localhost:8000
# - Knowledge base: http://localhost:8088
```

### Using the AI Assistant
Once running, you can interact with TI-Bot through:
- Web API endpoints
- Direct HTTP requests
- Integration with chat platforms like Slack

## 💡 Use Cases

**Technical Support**
- Troubleshoot code errors and issues
- Find documentation and best practices
- Get step-by-step guidance for complex tasks

**Information Retrieval**
- Search across multiple knowledge bases
- Find relevant tickets, issues, or discussions
- Access enterprise tool data quickly

**Contextual Assistance**
- Continue conversations from where you left off
- Get personalized responses based on your history
- Receive suggestions based on your patterns

## ⚙️ Architecture Overview

TI-Bot Deep consists of two main systems working together:

**Enhanced Pipeline**
- Advanced memory capabilities
- Better context understanding
- Improved response quality
- Cross-session conversation continuity

**Baseline Pipeline** 
- Basic question-answering functionality
- Simple knowledge base search
- Standard AI responses

Both systems include:
- RESTful APIs for easy integration
- Comprehensive logging and monitoring
- Scalable microservice architecture
- Enterprise security features

### 🔍 Baseline Pipeline Reference

Need to understand how the baseline Hades + Zion stack moves data from the HTTP edge to the knowledge base and back? Start with the [Baseline Pipeline Flow guide](docs/baseline-pipeline.md) for a box-and-arrow walkthrough plus file-level pointers for every stage.

## 🛠️ Development & Customization

### Configuration
The system can be customized through environment variables and configuration files:
- Database connections
- AI model settings
- Memory system parameters
- Integration endpoints

### Extension Points
- Add new enterprise tool integrations
- Customize response templates
- Implement domain-specific knowledge processing
- Extend memory and context capabilities

### API Integration
```bash
# Example: Ask a question via API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I fix a Python import error?"}'
```

## 📚 What's Included

- **Complete AI Assistant Pipeline**: Ready-to-deploy intelligent assistant
- **Memory System**: Conversational context and learning capabilities  
- **Knowledge Integration**: Connects to documentation and enterprise tools
- **API Endpoints**: Easy integration with existing systems
- **Docker Support**: Simplified deployment and scaling
- **Documentation**: Comprehensive guides and examples

## 🤝 Support & Contribution

This project is under poc exopsing multiple memory technique to explore enhancement and bulding intelligent AI assistants with memory, context awareness, and enterprise integration capabilities.

For technical questions or contributions, refer to the detailed documentation in each service directory.

---
