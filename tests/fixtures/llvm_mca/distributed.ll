define i32 @f(i32 %x, i32 %y, i32 %z) {
  %xy = mul i32 %x, %y
  %xz = mul i32 %x, %z
  %r = add i32 %xy, %xz
  ret i32 %r
}
