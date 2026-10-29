Minimal stand-ins for the COMSOL Java API (`com.comsol.model.*`) so that
`tests/test_java_compiles.py` can check the Java drivers for syntax and type
errors without COMSOL. They encode the call signatures the drivers assume; they
are **not** COMSOL and are never on the classpath of a real `comsol compile`.
