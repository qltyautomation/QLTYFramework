#!/bin/bash

###############################################################################
# QLTY Framework - Universal Installation Script
#
# This script sets up the QLTY test automation environment for any client project
#
# Usage:
#   # From client wrapper script:
#   curl -fsSL https://raw.githubusercontent.com/yourusername/QLTYFivable/main/install.sh | bash
#
#   # Direct installation with repo parameter:
#   curl -fsSL https://raw.githubusercontent.com/qltyautomation/QLTYFramework/main/install.sh | bash -s -- --repo https://bitbucket.org/fivable/lms-testing.git
#
#   # Or locally:
#   ./install.sh --repo https://github.com/yourusername/ClientTests.git
#
###############################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
VENV_NAME=""  # Will be set based on client repo name
PYTHON_VERSION="python3"
INSTALL_DIR="$HOME/QLTYAutomation"
FRAMEWORK_REPO="https://github.com/qltyautomation/QLTYFramework"
CLIENT_REPO=""
CLIENT_NAME=""

# Function to print colored messages
print_info() {
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to extract repo name from URL
get_repo_name() {
    local url="$1"
    # Extract repo name from URL (e.g., https://github.com/user/repo.git -> repo)
    basename "$url" .git
}

# Function to convert HTTPS URL to SSH URL
convert_to_ssh() {
    local url="$1"
    # Convert https://hostname/user/repo.git to git@hostname:user/repo.git
    if [[ "$url" =~ ^https://([^/]+)/(.+)$ ]]; then
        local hostname="${BASH_REMATCH[1]}"
        local path="${BASH_REMATCH[2]}"
        echo "git@${hostname}:${path}"
    else
        # Already SSH or unknown format, return as-is
        echo "$url"
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --repo URL          Client test repository URL (required)
    --framework URL     Framework repository URL (default: $FRAMEWORK_REPO)
    --install-dir DIR   Installation directory (default: $INSTALL_DIR)
    --ssh               Use SSH for git clone (converts HTTPS URLs to SSH)
    --help              Show this help message

Examples:
    $0 --repo https://github.com/yourusername/ClientTests.git
    $0 --repo https://bitbucket.org/fivable/lms-testing.git --ssh
    $0 --repo git@bitbucket.org:fivable/lms-testing.git

Environment Variables:
    CLIENT_REPO         Can be used instead of --repo flag
EOF
}

# Parse command line arguments
CLIENT_REPO_FROM_ARG=""
USE_SSH=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo)
            CLIENT_REPO="$2"
            CLIENT_REPO_FROM_ARG="$2"
            shift 2
            ;;
        --framework)
            FRAMEWORK_REPO="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --ssh)
            USE_SSH=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Convert URLs to SSH if --ssh flag is set
if [ "$USE_SSH" = true ]; then
    CLIENT_REPO=$(convert_to_ssh "$CLIENT_REPO")
    FRAMEWORK_REPO=$(convert_to_ssh "$FRAMEWORK_REPO")
fi

# Header
echo ""
echo "============================================================="
echo "  QLTY Framework - Universal Installation Script"
echo "============================================================="
echo ""

# Check if CLIENT_REPO is set (either from args or environment)
if [ -z "$CLIENT_REPO" ]; then
    print_error "Client repository URL is required"
    echo ""
    show_usage
    exit 1
fi

# Extract client name from repo URL
CLIENT_NAME=$(get_repo_name "$CLIENT_REPO")
VENV_NAME="qlty-$(echo "$CLIENT_NAME" | tr '[:upper:]' '[:lower:]')"

print_info "Client Repository: $CLIENT_REPO"
print_info "Client Name: $CLIENT_NAME"
print_info "Virtual Environment: $VENV_NAME"
print_info "Installation Directory: $INSTALL_DIR"

# Check if running from local directory or remote
# Only skip clone if running locally (no --repo provided) AND test_runner.py exists
if [ -z "$CLIENT_REPO_FROM_ARG" ] && [ -f "$(pwd)/test_runner.py" ]; then
    print_info "Running from local client directory, skipping clone..."
    SKIP_CLONE=true
    CURRENT_DIR="$(pwd)"
    INSTALL_DIR="$(dirname "$CURRENT_DIR")"
    FRAMEWORK_PATH="$INSTALL_DIR/QLTYFramework"
else
    SKIP_CLONE=false
    FRAMEWORK_PATH="$INSTALL_DIR/QLTYFramework"
fi

# Check Git installation
if [ "$SKIP_CLONE" = false ]; then
    print_info "Checking Git installation..."
    if ! command_exists git; then
        print_error "Git is not installed. Please install Git first."
        exit 1
    fi
    print_success "Git found"
fi

# Check Python installation
print_info "Checking Python installation..."
if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VER=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VER found"

# Check pip installation
print_info "Checking pip installation..."
if ! command_exists pip3; then
    print_error "pip3 is not installed. Please install pip3."
    exit 1
fi
print_success "pip3 found"

# Check virtualenv installation
print_info "Checking virtualenv installation..."
if ! command_exists virtualenv; then
    print_warning "virtualenv not found. Installing..."
    pip3 install virtualenv
    print_success "virtualenv installed"
else
    print_success "virtualenv found"
fi

# Clone repositories if needed
if [ "$SKIP_CLONE" = false ]; then
    # Create installation directory
    print_info "Creating installation directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Clone QLTYFramework
    print_info "Cloning QLTYFramework repository..."
    if [ -d "QLTYFramework" ]; then
        print_warning "QLTYFramework directory already exists"
        if [ -t 0 ]; then  # Check if running interactively
            read -p "Do you want to remove it and re-clone? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf QLTYFramework
                git clone "$FRAMEWORK_REPO" QLTYFramework
                print_success "QLTYFramework cloned"
            else
                print_info "Using existing QLTYFramework directory"
            fi
        else
            # Non-interactive mode: remove and re-clone to ensure clean state
            print_info "Non-interactive mode: Removing and re-cloning QLTYFramework..."
            rm -rf QLTYFramework
            git clone "$FRAMEWORK_REPO" QLTYFramework
            print_success "QLTYFramework cloned"
        fi
    else
        git clone "$FRAMEWORK_REPO" QLTYFramework
        print_success "QLTYFramework cloned"
    fi

    # Clone client repository
    print_info "Cloning $CLIENT_NAME repository..."
    if [ -d "$CLIENT_NAME" ]; then
        print_warning "$CLIENT_NAME directory already exists"
        if [ -t 0 ]; then  # Check if running interactively
            read -p "Do you want to remove it and re-clone? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$CLIENT_NAME"
                git clone "$CLIENT_REPO" "$CLIENT_NAME"
                print_success "$CLIENT_NAME cloned"
            else
                print_info "Using existing $CLIENT_NAME directory"
            fi
        else
            # Non-interactive mode: remove and re-clone to ensure clean state
            print_info "Non-interactive mode: Removing and re-cloning $CLIENT_NAME..."
            rm -rf "$CLIENT_NAME"
            git clone "$CLIENT_REPO" "$CLIENT_NAME"
            print_success "$CLIENT_NAME cloned"
        fi
    else
        git clone "$CLIENT_REPO" "$CLIENT_NAME"
        print_success "$CLIENT_NAME cloned"
    fi

    # Change to client directory
    cd "$CLIENT_NAME"
    CURRENT_DIR="$(pwd)"
fi

print_info "Working directory: $CURRENT_DIR"
print_info "Framework path: $FRAMEWORK_PATH"

# Create virtual environment
print_info "Creating virtual environment: $VENV_NAME"
if [ -d "$HOME/.virtualenvs/$VENV_NAME" ]; then
    print_warning "Virtual environment already exists at $HOME/.virtualenvs/$VENV_NAME"
    if [ -t 0 ]; then  # Check if running interactively
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing virtual environment..."
            rm -rf "$HOME/.virtualenvs/$VENV_NAME"
            virtualenv -p $PYTHON_VERSION "$HOME/.virtualenvs/$VENV_NAME"
            print_success "Virtual environment recreated"
        else
            print_info "Using existing virtual environment"
        fi
    else
        print_info "Non-interactive mode: Using existing virtual environment"
    fi
else
    mkdir -p "$HOME/.virtualenvs"
    virtualenv -p $PYTHON_VERSION "$HOME/.virtualenvs/$VENV_NAME"
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$HOME/.virtualenvs/$VENV_NAME/bin/activate"
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip
print_success "pip upgraded"

# Check if QLTYFramework exists
print_info "Checking for QLTYFramework..."
if [ -d "$FRAMEWORK_PATH" ]; then
    print_success "QLTYFramework found at $FRAMEWORK_PATH"

    # Install QLTYFramework in editable mode
    print_info "Installing QLTYFramework in editable mode..."
    pip install -e "$FRAMEWORK_PATH"
    print_success "QLTYFramework installed"
else
    print_error "QLTYFramework not found at $FRAMEWORK_PATH"
    print_info "Please ensure QLTYFramework is available"
    exit 1
fi

# Install additional dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    print_info "Installing additional dependencies from requirements.txt..."
    pip install -r requirements.txt
    print_success "Additional dependencies installed"
fi

# Verify installation
print_info "Verifying installation..."
python -c "import qlty; print('QLTYFramework location:', qlty.__file__)" 2>/dev/null
if [ $? -eq 0 ]; then
    print_success "QLTYFramework imported successfully"
else
    print_warning "Could not verify QLTYFramework import"
fi

# Check for settings.py
print_info "Checking for settings.py..."
if [ -f "settings.py" ]; then
    print_success "settings.py found"
else
    print_warning "settings.py not found. You'll need to create it before running tests."
    print_info "See README.md for configuration instructions"
fi

# Check for drivers directory
print_info "Checking drivers directory..."
if [ -d "drivers" ]; then
    print_success "drivers directory found"

    # List available drivers
    if [ "$(ls -A drivers 2>/dev/null)" ]; then
        print_info "Available drivers:"
        ls -1 drivers/ | sed 's/^/  - /'
    else
        print_warning "drivers directory is empty"
        print_info "You may need to download ChromeDriver or other WebDriver binaries"
    fi
else
    print_warning "drivers directory not found"
fi

# Print installation summary
echo ""
echo "============================================================="
echo "  Installation Complete!"
echo "============================================================="
echo ""
print_success "Client: $CLIENT_NAME"
print_success "Installation directory: $CURRENT_DIR"
print_success "Virtual environment: $HOME/.virtualenvs/$VENV_NAME"
echo ""
print_info "To activate the virtual environment, run:"
echo "  source $HOME/.virtualenvs/$VENV_NAME/bin/activate"
echo ""
print_info "To navigate to the project directory, run:"
echo "  cd $CURRENT_DIR"
echo ""
print_info "To run tests, use:"
echo "  python test_runner.py -p chrome"
echo "  python test_runner.py -p chrome -s    # With Slack notifications"
echo "  python test_runner.py -p chrome -r    # With TestRail integration"
echo ""
print_info "For more options, see:"
echo "  python test_runner.py --help"
echo ""

# Offer to keep environment activated
if [ -t 0 ]; then  # Check if running interactively
    read -p "Keep virtual environment activated? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_success "Virtual environment remains activated"
        echo ""
        print_info "Current Python: $(which python)"
        print_info "Current pip: $(which pip)"
    else
        deactivate 2>/dev/null || true
        print_info "Virtual environment deactivated"
    fi
else
    print_info "Non-interactive mode: Virtual environment remains activated"
fi

echo ""
print_success "Setup complete! Happy testing!"
echo ""
