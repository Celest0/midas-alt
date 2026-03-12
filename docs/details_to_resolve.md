# MIDAS App Behavior Notes

Notepad for details encountered during dev process which need to be discussed/resolved to ensure behavior is as expected.

- [ ] [src](../src/simulation/data_generation/data_generator_base.py) - When generating an age using the `sample_year_constructed()` method the provided max_age is to allow the different instances of entities to define an upper bound to their age. Due to the clamping nature of the implementation this will skew all the results to be on the older end of the distribution