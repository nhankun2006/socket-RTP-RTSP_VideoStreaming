cmake_minimum_required(VERSION 3.20)

project(RTSP_RTP_Socket_Client)

set(CMAKE_C_COMPILER "C:/ProgramData/mingw64/mingw64/bin/gcc.exe")
set(CMAKE_CXX_COMPILER "C:/ProgramData/mingw64/mingw64/bin/g++.exe")

file(DOWNLOAD
     https://github.com/cpm-cmake/CPM.cmake/releases/download/v0.38.3/CPM.cmake
     "${CMAKE_BINARY_DIR}/CPM.cmake"
)
include("${CMAKE_BINARY_DIR}/CPM.cmake")

set(BUILD_SHARED_LIBS ON)

set(SDL2TTF_VENDORED ON CACHE BOOL "Enable vendored mode" FORCE)
set(SDL2TTF_HARFBUZZ ON CACHE BOOL "Enable harfbuzz" FORCE)

# 1. Add Package
CPMAddPackage("gh:libsdl-org/SDL#release-2.28.5")
CPMAddPackage(
    NAME SDL2_ttf
    GITHUB_REPOSITORY libsdl-org/SDL_ttf
    GIT_TAG release-2.20.2
    # IMPORTANT: We must tell CPM to download the "external" folder 
    # because that is where the vendored FreeType code lives!
    GIT_SUBMODULES "external/freetype" "external/harfbuzz" 
)

# compile all source files .cpp in client/ directory
file(GLOB_RECURSE SOURCES "client/*.cpp")
add_executable(client_app ${SOURCES})

# 3. The Magic: Link them
# This AUTOMATICALLY sets up the -I (include) and -L (lib) paths for you!
target_link_libraries(client_app PRIVATE 
    SDL2::SDL2 
    SDL2::SDL2main
    SDL2_ttf::SDL2_ttf
    ws2_32  # <--- CRITICAL: This fixes the "__imp_WSAStartup" errors!
)

# 3. The Magic Copy Command
# This command runs AFTER the build finishes.
# $<TARGET_FILE:SDL2::SDL2> finds the DLL path automatically.
# $<TARGET_FILE_DIR:client_app> finds your executable's folder automatically.
add_custom_command(TARGET client_app POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
    $<TARGET_FILE:SDL2::SDL2>
    $<TARGET_FILE_DIR:client_app>
    COMMENT "Copying SDL2 DLL to output directory..."
)

# copy dll files for Windows
if(WIN32)
    add_custom_command(TARGET client_app POST_BUILD
        # Copy SDL2.dll
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:SDL2::SDL2>
            $<TARGET_FILE_DIR:client_app>
        
        # Copy SDL2_ttf.dll
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:SDL2_ttf::SDL2_ttf>
            $<TARGET_FILE_DIR:client_app>

        # Bonus: Sometimes FreeType is built as a separate DLL. 
        # If the build fails saying "freetype.dll missing", uncomment the lines below:
        # COMMAND ${CMAKE_COMMAND} -E copy_if_different
        #     $<TARGET_FILE:freetype>
        #     $<TARGET_FILE_DIR:client_app>

        COMMENT "Copying dynamic libraries (.dll) to executable directory..."
    )
endif()