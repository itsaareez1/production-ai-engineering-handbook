"""Atlas: the modules that the book's later listings import.

The book prints each listing as a standalone file under listings/.
This package holds the two pieces that are reused:

    atlas.validation  the answer schema and validator of Listing 12.1,
                      imported by Listing 33.1
    atlas.api         the minimal service entry point that the
                      Dockerfile of Listing 44.1 starts
"""
__all__ = ["validation"]
__version__ = "1.0.0"
