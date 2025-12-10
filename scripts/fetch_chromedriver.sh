#!/bin/bash

###############################################################################
# ChromeDriver Fetcher
#
# Downloads the correct ChromeDriver version based on installed Chrome
#
# Usage:
#   ./fetch_chromedriver.sh                    # Install to ./drivers
#   ./fetch_chromedriver.sh --output ~/drivers # Install to custom directory
#   ./fetch_chromedriver.sh --check            # Just check versions, don't download
#
###############################################################################

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Function to get installed Chrome version
get_chrome_version() {
    local chrome_version=""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if [ -d "/Applications/Google Chrome.app" ]; then
            chrome_version=$("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists google-chrome; then
            chrome_version=$(google-chrome --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        elif command_exists google-chrome-stable; then
            chrome_version=$(google-chrome-stable --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        elif command_exists chromium-browser; then
            chrome_version=$(chromium-browser --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        fi
    fi

    echo "$chrome_version"
}

# Function to get platform string for Chrome for Testing
get_chrome_platform() {
    local arch=$(uname -m)

    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [[ "$arch" == "arm64" ]]; then
            echo "mac-arm64"
        else
            echo "mac-x64"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux64"
    else
        echo ""
    fi
}

# Function to get existing ChromeDriver version
get_chromedriver_version() {
    local driver_path="$1"
    if [ -f "$driver_path" ]; then
        "$driver_path" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1
    fi
}

# Function to find ChromeDriver URL for a given Chrome version
get_chromedriver_url() {
    local chrome_version="$1"
    local platform="$2"
    local major_version=$(echo "$chrome_version" | cut -d'.' -f1)

    local json_url="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
    local versions_json=$(curl -fsSL "$json_url" 2>/dev/null)

    if [ -z "$versions_json" ]; then
        return 1
    fi

    echo "$versions_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
target_version = '$chrome_version'
major = '$major_version'
platform = '$platform'

# Try exact match first
for v in data.get('versions', []):
    if v['version'] == target_version:
        downloads = v.get('downloads', {}).get('chromedriver', [])
        for d in downloads:
            if d['platform'] == platform:
                print(d['url'])
                sys.exit(0)

# Fall back to latest version with same major
best_match = None
for v in data.get('versions', []):
    if v['version'].startswith(major + '.'):
        downloads = v.get('downloads', {}).get('chromedriver', [])
        for d in downloads:
            if d['platform'] == platform:
                best_match = d['url']

if best_match:
    print(best_match)
" 2>/dev/null
}

# Function to download and install ChromeDriver
install_chromedriver() {
    local target_dir="$1"
    local chrome_version=$(get_chrome_version)
    local platform=$(get_chrome_platform)

    if [ -z "$chrome_version" ]; then
        print_error "Could not detect Chrome version."
        print_info "Make sure Google Chrome is installed."
        return 1
    fi

    if [ -z "$platform" ]; then
        print_error "Unsupported platform: $OSTYPE"
        return 1
    fi

    print_info "Detected Chrome version: $chrome_version"
    print_info "Platform: $platform"

    # Check existing ChromeDriver
    local existing_driver="$target_dir/chromedriver"
    if [ -f "$existing_driver" ]; then
        local existing_version=$(get_chromedriver_version "$existing_driver")
        if [ -n "$existing_version" ]; then
            print_info "Existing ChromeDriver version: $existing_version"
            local chrome_major=$(echo "$chrome_version" | cut -d'.' -f1)
            local driver_major=$(echo "$existing_version" | cut -d'.' -f1)
            if [ "$chrome_major" = "$driver_major" ]; then
                print_success "ChromeDriver is already compatible (same major version)"
                return 0
            else
                print_warning "ChromeDriver major version ($driver_major) differs from Chrome ($chrome_major)"
            fi
        fi
    fi

    # Find matching ChromeDriver URL
    print_info "Finding matching ChromeDriver..."
    local chromedriver_url=$(get_chromedriver_url "$chrome_version" "$platform")

    if [ -z "$chromedriver_url" ]; then
        print_error "Could not find matching ChromeDriver for Chrome $chrome_version"
        return 1
    fi

    # Extract version from URL
    local driver_version=$(echo "$chromedriver_url" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
    print_info "Found ChromeDriver version: $driver_version"
    print_info "Downloading from: $chromedriver_url"

    # Create target directory
    mkdir -p "$target_dir"

    # Download and extract
    local temp_zip=$(mktemp)
    local temp_dir=$(mktemp -d)

    if curl -fsSL "$chromedriver_url" -o "$temp_zip"; then
        print_info "Extracting ChromeDriver..."
        unzip -q -o "$temp_zip" -d "$temp_dir"

        # Find and move chromedriver binary
        local chromedriver_bin=$(find "$temp_dir" -name "chromedriver" -type f | head -1)
        if [ -n "$chromedriver_bin" ]; then
            mv "$chromedriver_bin" "$target_dir/chromedriver"
            chmod +x "$target_dir/chromedriver"
            print_success "ChromeDriver installed to $target_dir/chromedriver"

            # Verify installation
            local installed_version=$(get_chromedriver_version "$target_dir/chromedriver")
            print_success "Installed ChromeDriver version: $installed_version"
        else
            print_error "Could not find chromedriver binary in downloaded archive"
            rm -rf "$temp_zip" "$temp_dir"
            return 1
        fi

        rm -rf "$temp_zip" "$temp_dir"
        return 0
    else
        print_error "Failed to download ChromeDriver"
        rm -rf "$temp_zip" "$temp_dir"
        return 1
    fi
}

# Function to check versions without downloading
check_versions() {
    local chrome_version=$(get_chrome_version)
    local platform=$(get_chrome_platform)

    echo ""
    echo "============================================================="
    echo "  ChromeDriver Version Check"
    echo "============================================================="
    echo ""

    if [ -z "$chrome_version" ]; then
        print_error "Chrome not found"
        return 1
    fi

    print_info "Chrome version: $chrome_version"
    print_info "Platform: $platform"

    local chromedriver_url=$(get_chromedriver_url "$chrome_version" "$platform")
    if [ -n "$chromedriver_url" ]; then
        local available_version=$(echo "$chromedriver_url" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        print_info "Available ChromeDriver: $available_version"
        print_info "Download URL: $chromedriver_url"
    else
        print_warning "No matching ChromeDriver found"
    fi

    # Check for existing chromedriver in common locations
    echo ""
    print_info "Checking for existing ChromeDriver installations..."

    local search_paths=("./drivers/chromedriver" "./chromedriver" "/usr/local/bin/chromedriver")
    for path in "${search_paths[@]}"; do
        if [ -f "$path" ]; then
            local version=$(get_chromedriver_version "$path")
            print_info "Found: $path (version: $version)"
        fi
    done

    echo ""
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Downloads the correct ChromeDriver version based on your installed Chrome browser.

Options:
    --output DIR    Installation directory (default: ./drivers)
    --check         Check versions without downloading
    --help          Show this help message

Examples:
    $0                          # Install to ./drivers
    $0 --output ~/my-drivers    # Install to custom directory
    $0 --check                  # Just check versions

EOF
}

# Main
OUTPUT_DIR="./drivers"
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --check)
            CHECK_ONLY=true
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

if [ "$CHECK_ONLY" = true ]; then
    check_versions
else
    echo ""
    echo "============================================================="
    echo "  ChromeDriver Fetcher"
    echo "============================================================="
    echo ""
    install_chromedriver "$OUTPUT_DIR"
fi
