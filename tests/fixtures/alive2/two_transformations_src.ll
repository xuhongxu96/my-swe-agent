define i8 @foo(i8 %x) {
  %r = add i8 %x, 0
  ret i8 %r
}

define i8 @bar(i8 %x) {
  %r = mul i8 %x, 2
  ret i8 %r
}
