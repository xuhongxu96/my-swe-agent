define i32 @f(i32 %x, i32 %y, i32 %z) {
  %yz = add i32 %y, %z
  %r = mul i32 %x, %yz
  ret i32 %r
}
