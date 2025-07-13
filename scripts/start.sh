#!/bin/bash

# AIStudioProxy Start Script
# This script provides easy commands to start the application in different modes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  AIStudioProxy Launcher${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Function to check if Poetry is installed (for local development)
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_warning "Poetry is not installed. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# Function to start in production mode
start_production() {
    print_status "Starting AIStudioProxy in production mode..."
    
    # Create necessary directories
    mkdir -p logs auth profiles
    
    # Start with docker-compose
    docker-compose up -d
    
    print_status "AIStudioProxy is starting up..."
    print_status "API will be available at: http://localhost:2048"
    print_status "Metrics will be available at: http://localhost:9090"
    print_status "Use 'docker-compose logs -f' to view logs"
}

# Function to start in development mode
start_development() {
    print_status "Starting AIStudioProxy in development mode..."
    
    # Create necessary directories
    mkdir -p logs auth profiles
    
    # Start with development docker-compose
    docker-compose -f docker-compose.dev.yml up -d
    
    print_status "AIStudioProxy development environment is starting up..."
    print_status "API will be available at: http://localhost:2048"
    print_status "Auto-reload is enabled for development"
    print_status "Use 'docker-compose -f docker-compose.dev.yml logs -f' to view logs"
}

# Function to start locally (without Docker)
start_local() {
    print_status "Starting AIStudioProxy locally..."
    
    check_poetry
    
    # Install dependencies
    print_status "Installing dependencies..."
    poetry install
    
    # Install Playwright browsers
    print_status "Installing Playwright browsers..."
    poetry run playwright install chromium
    
    # Create necessary directories
    mkdir -p logs auth profiles
    
    # Start the application
    print_status "Starting application..."
    poetry run python -m src.main --reload --debug
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    if [ "$1" = "docker" ]; then
        # Run tests in Docker
        docker-compose -f docker-compose.dev.yml exec aistudio-proxy-dev poetry run pytest
    else
        # Run tests locally
        check_poetry
        poetry run pytest
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping AIStudioProxy services..."
    
    # Stop production services
    if [ -f "docker-compose.yml" ]; then
        docker-compose down
    fi
    
    # Stop development services
    if [ -f "docker-compose.dev.yml" ]; then
        docker-compose -f docker-compose.dev.yml down
    fi
    
    print_status "All services stopped."
}

# Function to show logs
show_logs() {
    if [ "$1" = "dev" ]; then
        docker-compose -f docker-compose.dev.yml logs -f
    else
        docker-compose logs -f
    fi
}

# Function to show status
show_status() {
    print_status "Checking service status..."
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Production services are running:"
        docker-compose ps
    else
        print_warning "No production services are running."
    fi
    
    if docker-compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up"; then
        print_status "Development services are running:"
        docker-compose -f docker-compose.dev.yml ps
    fi
    
    # Check API health
    if curl -s http://localhost:2048/health > /dev/null; then
        print_status "API is responding at http://localhost:2048"
    else
        print_warning "API is not responding at http://localhost:2048"
    fi
}

# Function to show help
show_help() {
    print_header
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  prod, production    Start in production mode (Docker)"
    echo "  dev, development    Start in development mode (Docker)"
    echo "  local              Start locally without Docker"
    echo "  test               Run tests locally"
    echo "  test-docker        Run tests in Docker"
    echo "  stop               Stop all services"
    echo "  logs               Show production logs"
    echo "  logs-dev           Show development logs"
    echo "  status             Show service status"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 prod            # Start in production mode"
    echo "  $0 dev             # Start in development mode"
    echo "  $0 local           # Start locally"
    echo "  $0 test            # Run tests"
    echo "  $0 stop            # Stop all services"
    echo ""
}

# Main script logic
main() {
    case "${1:-help}" in
        "prod"|"production")
            print_header
            check_docker
            start_production
            ;;
        "dev"|"development")
            print_header
            check_docker
            start_development
            ;;
        "local")
            print_header
            start_local
            ;;
        "test")
            run_tests
            ;;
        "test-docker")
            check_docker
            run_tests docker
            ;;
        "stop")
            stop_services
            ;;
        "logs")
            show_logs
            ;;
        "logs-dev")
            show_logs dev
            ;;
        "status")
            show_status
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"
