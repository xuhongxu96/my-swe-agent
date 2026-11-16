define i8 @foo(i8 %x) {
  ret i8 %x
}

define i8 @bar(i8 %x) {
  %r = shl i8 %x, 2
  ret i8 %r
}
