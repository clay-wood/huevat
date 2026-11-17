module HuevatMakieExt
using Huevat, Makie
function Huevat.makie(g::Huevat.Gradient; limits=(0.,1.), center=nothing,
                     n=1025, missing=:transparent, under=nothing, over=nothing)
    lo,hi = limits
    Huevat.limits(lo,hi,center)
    colors = Huevat.colormap(g;n)
    scale = Makie.ReversibleScale(x -> Huevat.normalize(x,lo,hi,center),
                                  t -> Huevat.denormalize(t,lo,hi,center))
    (colormap=colors,colorrange=(lo,hi),colorscale=scale,nan_color=missing,
     lowclip=under === nothing ? first(colors) : under,
     highclip=over === nothing ? last(colors) : over)
end
end
