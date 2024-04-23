add_executable(profiler Profiler.cpp)
target_link_libraries(profiler PUBLIC ProfilerLib)
install(TARGETS profiler DESTINATION bin)

