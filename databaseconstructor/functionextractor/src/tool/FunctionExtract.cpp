#include <clang/Rewrite/Core/Rewriter.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <clang/Tooling/Refactoring.h>
#include <clang/Frontend/TextDiagnosticPrinter.h>

#include <llvm/Support/CommandLine.h>
#include <llvm/Support/raw_ostream.h>
#include <type_traits>
#include <iostream>

#include "FunctionExtractor.hpp"
#include "FunctionProcess.hpp"
#include "RenameFunction.hpp"
#include "RenameGlobal.hpp"

using namespace llvm;
using namespace clang;
using namespace clang::tooling;
using namespace clang::ast_matchers;

namespace {

enum class ToolMode { Extract, Process, Rename, RenameGlobal};

cl::OptionCategory ToolOptions("options");

cl::opt<ToolMode>
    Mode("mode", cl::desc("Target functions to be extracted."),
         cl::values(clEnumValN(ToolMode::Extract, "extract",
                               "Extract functions with nemeric input args, return type, no external function calls, and no global accesses."
                               "The default mode."),
                    clEnumValN(ToolMode::Process, "process",
                               "Process functions to remove externel function calls."),
                    clEnumValN(ToolMode::Rename, "rename",
                               "Rename function name."),
                    clEnumValN(ToolMode::RenameGlobal, "rename-global",
                               "Rename global variables.")
                               ),
         cl::init(ToolMode::Extract),
         cl::cat(ToolOptions));

bool applyReplacements(RefactoringTool &Tool) {
    LangOptions DefaultLangOptions;
    IntrusiveRefCntPtr<DiagnosticOptions> DiagOpts = new DiagnosticOptions();
    clang::TextDiagnosticPrinter DiagnosticPrinter(errs(), &*DiagOpts);
    DiagnosticsEngine Diagnostics(
        IntrusiveRefCntPtr<DiagnosticIDs>(new DiagnosticIDs()), &*DiagOpts,
        &DiagnosticPrinter, false);
    auto &FileMgr = Tool.getFiles();
    SourceManager Sources(Diagnostics, FileMgr);

    Rewriter Rewrite(Sources, DefaultLangOptions);

    bool Result = true;
    for (const auto &FileAndReplaces : groupReplacementsByFile(
             Rewrite.getSourceMgr().getFileManager(), Tool.getReplacements())) {
        auto &CurReplaces = FileAndReplaces.second;

        Result = applyAllReplacements(CurReplaces, Rewrite) && Result;
    }
    if (!Result) {
        llvm::errs() << "Failed applying all replacements.\n";
        return false;
    }

    return !Rewrite.overwriteChangedFiles();
}

template <typename InstrTool> int runToolOnCode(RefactoringTool &Tool) {
    InstrTool Instr(Tool.getReplacements());
    ast_matchers::MatchFinder Finder;
    Instr.registerMatchers(Finder);
    std::unique_ptr<tooling::FrontendActionFactory> Factory =
        tooling::newFrontendActionFactory(&Finder);

    auto Ret = Tool.run(Factory.get());
    if (std::is_same<InstrTool, extractor::FunctionExtractor>::value) {
        return Ret;
    }
    if (!Ret)
        if (!applyReplacements(Tool)) {
            llvm::errs() << "Failed to overwrite the input files.\n";
            return 1;
        }

    return Ret;
}


} // namespace

int main(int argc, const char **argv) {
    auto ExpectedParser =
        CommonOptionsParser::create(argc, argv, ToolOptions);
    if (!ExpectedParser) {
        llvm::errs() << ExpectedParser.takeError();
        return 1;
    }
    CommonOptionsParser &OptionsParser = ExpectedParser.get();

    const auto &Compilations = OptionsParser.getCompilations();
    const auto &Files = OptionsParser.getSourcePathList();
    RefactoringTool Tool(Compilations, Files);
    int Result = 0;

    if (Mode == ToolMode::Extract) {
        Result = runToolOnCode<extractor::FunctionExtractor>(Tool);
        if (Result) {
            llvm::errs() << "Something went wrong...\n";
            return Result;
        }
    } else if (Mode == ToolMode::Process) {
        Result = runToolOnCode<process::FunctionProcess>(Tool);
        if (Result) {
            llvm::errs() << "Something went wrong...\n";
            return Result;
        }
    } else if (Mode == ToolMode::Rename) {
        Result = runToolOnCode<process::RenameFunction>(Tool);
        if (Result) {
            llvm::errs() << "Something went wrong...\n";
            return Result;
        }
    } else if (Mode == ToolMode::RenameGlobal) {
        Result = runToolOnCode<process::RenameGlobal>(Tool);
        if (Result) {
            llvm::errs() << "Something went wrong...\n";
            return Result;
        }
    }

    return 0;
}