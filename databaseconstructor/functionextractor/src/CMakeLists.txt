add_library(FunctionExtractorLib
    Utils.cpp
    RuleActionCallback.cpp
    FunctionPrinter.cpp
    FunctionExtractor.cpp
    FunctionProcess.cpp
    ProcessCall.cpp
    RenameFunction.cpp
    RenameGlobal.cpp
)
target_include_directories(FunctionExtractorLib PUBLIC ${CLANG_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS} ${CMAKE_CURRENT_SOURCE_DIR})

if(CLANG_LINK_CLANG_DYLIB)
    target_link_libraries(FunctionExtractorLib PUBLIC LLVM)
    clang_target_link_libraries(FunctionExtractorLib PUBLIC)
else()
    llvm_map_components_to_libnames(llvm_libs support core)
    target_link_libraries(FunctionExtractorLib PUBLIC ${llvm_libs}
                                                   clangASTMatchers
                                                   clangTransformer
                                                   clangTooling)
endif(CLANG_LINK_CLANG_DYLIB)

add_subdirectory(tool)
