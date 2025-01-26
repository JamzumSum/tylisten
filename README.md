# tylisten

A tiny hook specification library with typing support.

[![python](https://img.shields.io/pypi/pyversions/tylisten?logo=python&logoColor=white)][home]
[![version](https://img.shields.io/pypi/v/tylisten?logo=python)][pypi]
[![style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This library is the hook framework used by [aioqzone][aioqzone] and [Qzone2TG][Qzone2TG].

## Feature

- [x] Tiny & Easy to use
- [x] **Fully** typing support
- [x] **Zero** dependencies!

# Documentation

Since version 2.0.0, we've built [documents][doc] with _Sphinx_.

## Examples

For hook specifications, see:

- [qqqr.message](https://github.com/aioqzone/aioqzone/blob/beta/src/qqqr/message.py)
- [aioqzone.message](https://github.com/aioqzone/aioqzone/blob/beta/src/aioqzone/message.py)
- [aioqzone_feed.message](https://github.com/aioqzone/aioqzone-feed/blob/beta/src/aioqzone_feed/message)

For hook implementations, see:

- [qzone3tg.app.base._hook](https://github.com/aioqzone/Qzone2TG/blob/beta/src/qzone3tg/app/base/_hook.py)
- [qzone3tg.app.interact._hook](https://github.com/aioqzone/Qzone2TG/blob/beta/src/qzone3tg/app/interact/_hook.py)

## License

```
MIT License

Copyright (c) 2023-2025 JamzumSum

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


[home]: https://github.com/JamzumSum/tylisten "A tiny hook specification library with typing support."
[pypi]: https://pypi.org/project/tylisten "A tiny hook specification library with typing support."
[aioqzone]: https://github.com/aioqzone/aioqzone "A python wrapper for Qzone web login and Qzone http api."
[Qzone2TG]: https://github.com/aioqzone/Qzone2TG "Forward Qzone Feeds to Telegram."
[doc]: https://jamzumsum.github.io/tylisten "tylisten documentation"
