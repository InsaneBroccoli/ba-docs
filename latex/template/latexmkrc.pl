# .latexmkrc — place in the same directory as main.tex
#
# Build with:   latexmk -pdf main.tex
# Clean with:   latexmk -C
#
# Full build chain handled automatically:
#   pdflatex → biber → makeglossaries → pdflatex × 2

# --- PDF mode by default -----------------------------------------------------
$pdf_mode = 1;               # 1 = pdflatex,  5 = xelatex via lualatex
# $pdf_mode = 5;             # uncomment if you switch to XeLaTeX/LuaLaTeX

# --- Glossaries integration ---------------------------------------------------
# latexmk does not natively detect glossary dependencies. The following custom
# dependency rule watches for changes in .glo, .acn, and .slo files (produced
# by glossaries-extra for the main glossary, acronyms, and symbols lists
# respectively) and runs makeglossaries when needed.

add_cus_dep('glo', 'gls', 0, 'run_makeglossaries');
add_cus_dep('acn', 'acr', 0, 'run_makeglossaries');
add_cus_dep('slo', 'sls', 0, 'run_makeglossaries');

sub run_makeglossaries {
    my ($base_name, $path) = fileparse( $_[0] );
    my @args = ( "-d", $path, $base_name );
    if ($silent) { unshift @args, "-q"; }
    return system "makeglossaries", @args;
}

# Tell latexmk that these extensions are generated files it should track
push @generated_exts, 'glo', 'gls', 'glg';     # glossary
push @generated_exts, 'acn', 'acr', 'alg';     # acronyms
push @generated_exts, 'slo', 'sls', 'slg';     # symbols / nomenclature

# --- Extra clean extensions ---------------------------------------------------
# Removed by latexmk -C (full clean)
$clean_ext .= ' %R.ist %R.xdy '
            . ' %R.glo %R.gls %R.glg '
            . ' %R.acn %R.acr %R.alg '
            . ' %R.slo %R.sls %R.slg '
            . ' %R.bbl %R.run.xml ';
