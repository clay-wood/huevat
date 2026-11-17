module HuevatPlotsExt
using Huevat, Plots
function Huevat.plots(g::Huevat.Gradient; limits=(0.,1.), center=nothing,n=1025)
    lo,hi = limits
    Huevat.limits(lo,hi,center)
    # Explicit stop positions keep an asymmetric physical center exact.
    t = collect(range(0,1;length=n))
    push!(t,0.5);sort!(unique!(t))
    positions = [(Huevat.denormalize(v,lo,hi,center)-lo)/(hi-lo) for v in t]
    (c=Plots.cgrad(Huevat.at.(Ref(g),t),positions),clims=(lo,hi))
end
end
