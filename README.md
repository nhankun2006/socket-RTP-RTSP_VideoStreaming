## 🛠️ Building the Project

We use **CMake** and **CPM / vcpkg** to handle dependencies automatically.

### Prerequisites

#### Windows
1.  **CMake**
2.  Install [vcpkg](https://github.com/microsoft/vcpkg) and allow it to integrate:
    ```bash
    git clone https://github.com/microsoft/vcpkg.git
    ./vcpkg/bootstrap-vcpkg.sh  # (Use .bat on Windows)
    ```
3.  **MinGW C++ Compiler** 64 bit
4.  **Ninja Build System**
    * Install via Chocolatey: `choco install ninja`
    * Or via Scoop: `scoop install ninja`
    * Or download the binary and add it to PATH.

#### Linux (Debian/Ubuntu, Fedora, Arch)
1.  **Basic Build Tools & CMake**
    * **Debian/Ubuntu:** `sudo apt update && sudo apt install build-essential cmake ninja-build git pkg-config`
    * **Fedora/RHEL:** `sudo dnf groupinstall "Development Tools" && sudo dnf install cmake ninja-build git pkgconf`
    * **Arch Linux:** `sudo pacman -S base-devel cmake ninja git`
2.  **SDL2 Dependencies (Required for Client UI)**
    * **Debian/Ubuntu:** `sudo apt install libsdl2-dev libsdl2-ttf-dev`
    * **Fedora/RHEL:** `sudo dnf install SDL2-devel SDL2_ttf-devel`
    * **Arch Linux:** `sudo pacman -S sdl2 sdl2_ttf`

### How to Build
Run these commands in the project folder. Replace `[path/to/vcpkg]` with your actual vcpkg location if you are building on Windows with vcpkg.

### Build Command
```bash
cmake -G "Ninja" -B build -S .
cmake --build build
```
*(Note for Linux users: Currently, this project heavily relies on Windows Sockets (`winsock2.h` / `ws2_32`). To make it fully cross-platform for Linux, you will need to replace the Winsock API with standard POSIX `<sys/socket.h>` or use a cross-platform library like `Boost.Asio`.)*