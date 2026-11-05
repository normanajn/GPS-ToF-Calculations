cmake_minimum_required(VERSION 3.16)
project(gps-tof VERSION 0.6.0 LANGUAGES NONE)

# Pure-Python project.  CMake provides a bootstrap target (venv + editable install),
# a ctest entry that runs pytest inside that venv, and installation of the man pages.
find_package(Python3 3.9 COMPONENTS Interpreter REQUIRED)

set(VENV_DIR ${CMAKE_SOURCE_DIR}/venv)
if(WIN32)
    set(VENV_PY ${VENV_DIR}/Scripts/python.exe)
else()
    set(VENV_PY ${VENV_DIR}/bin/python)
endif()

add_custom_command(
    OUTPUT ${VENV_PY}
    COMMAND ${Python3_EXECUTABLE} -m venv ${VENV_DIR}
    COMMAND ${VENV_PY} -m pip install --upgrade pip
    COMMAND ${VENV_PY} -m pip install -e "${CMAKE_SOURCE_DIR}[test]"
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Creating the gps-tof virtual environment")
add_custom_target(bootstrap ALL DEPENDS ${VENV_PY})

enable_testing()
add_test(NAME pytest COMMAND ${VENV_PY} -m pytest -q WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

install(FILES man/gps-tof.1 man/gps-tof-nmea.1 man/gps-tof-fscs.1 DESTINATION share/man/man1)
install(FILES man/gps_tof.3 DESTINATION share/man/man3)
install(FILES man/gps-tof.5 DESTINATION share/man/man5)
