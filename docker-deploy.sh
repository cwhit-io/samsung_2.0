#!/bin/bash
# Docker build and deployment script for Samsung TV Controller

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="samsung-tv-controller"
CONTAINER_NAME="samsung-tv-controller"
PORT="8002"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to build the Docker image
build_image() {
    print_status "Building Docker image: $IMAGE_NAME"
    
    if docker build -t $IMAGE_NAME .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to stop and remove existing container
cleanup_container() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        print_status "Stopping existing container: $CONTAINER_NAME"
        docker stop $CONTAINER_NAME
    fi
    
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        print_status "Removing existing container: $CONTAINER_NAME"
        docker rm $CONTAINER_NAME
    fi
}

# Function to create necessary directories
prepare_directories() {
    print_status "Preparing directories"
    mkdir -p logs
    
    # Create empty tokens.json if it doesn't exist
    if [ ! -f tokens.json ]; then
        echo '{}' > tokens.json
        print_status "Created empty tokens.json file"
    fi
}

# Function to run the container
run_container() {
    print_status "Starting container: $CONTAINER_NAME"
    
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:$PORT \
        -v "$(pwd)/tokens.json:/app/tokens.json" \
        -v "$(pwd)/logs:/app/logs" \
        -v "$(pwd)/config/config.json:/app/config/config.json:ro" \
        --network bridge \
        $IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        print_success "Container started successfully"
        print_status "API available at: http://localhost:$PORT"
        print_status "API Documentation: http://localhost:$PORT/docs"
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Function to show container logs
show_logs() {
    print_status "Container logs:"
    docker logs -f $CONTAINER_NAME
}

# Function to show container status
show_status() {
    print_status "Container status:"
    docker ps -f name=$CONTAINER_NAME
    
    print_status "Health check:"
    docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null || echo "No health check available"
}

# Main execution
case "${1:-build-and-run}" in
    build)
        check_docker
        build_image
        ;;
    run)
        check_docker
        prepare_directories
        cleanup_container
        run_container
        ;;
    build-and-run)
        check_docker
        build_image
        prepare_directories
        cleanup_container
        run_container
        ;;
    stop)
        docker stop $CONTAINER_NAME 2>/dev/null || print_warning "Container not running"
        ;;
    restart)
        docker restart $CONTAINER_NAME 2>/dev/null || print_error "Container not found"
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        cleanup_container
        docker rmi $IMAGE_NAME 2>/dev/null || print_warning "Image not found"
        print_success "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 {build|run|build-and-run|stop|restart|logs|status|clean}"
        echo ""
        echo "Commands:"
        echo "  build          - Build Docker image only"
        echo "  run            - Run container (assumes image exists)"
        echo "  build-and-run  - Build image and run container (default)"
        echo "  stop           - Stop running container"
        echo "  restart        - Restart container"
        echo "  logs           - Show container logs"
        echo "  status         - Show container status"
        echo "  clean          - Stop container and remove image"
        exit 1
        ;;
esac