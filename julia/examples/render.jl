using Huevat, CairoMakie
using Huevat.Colors: red, green, blue
import Plots
using Test

output=joinpath(@__DIR__,"..","..","artifacts","h5","julia")
mkpath(output)
g=Huevat.gradient(:diverging)
z=[8exp(-((x-.7)^2+y^2))-2exp(-((x+1)^2+y^2)/.4) for x in range(-3,3;length=100),y in range(-2,2;length=70)]
z[1,1]=0.
fig=Figure(size=(850,360))
ax=Axis(fig[1,1],title="Makie · centered at zero")
settings=Huevat.makie(g;limits=(-2.,8.),center=0.)
@test settings.colorscale(0.) == 0.5
@test settings.colorscale.inverse(0.5) == 0.
hm=heatmap!(ax,z;settings...)
actual=Makie.numbers_to_colors([0.],Makie.to_colormap(settings.colormap),settings.colorscale,
    Makie.Vec2f(-2,8),Makie.RGBAf(first(settings.colormap)),Makie.RGBAf(last(settings.colormap)),
    Makie.RGBAf(0,0,0,0),true)[1]
@test maximum(abs.([red(actual),green(actual),blue(actual)].-[red(at(g,.5)),green(at(g,.5)),blue(at(g,.5))])) < 2e-7
Colorbar(fig[1,2],hm)
ax2=Axis(fig[1,3],title="Categorical palettes",yticks=(1:3,["Core","Earth","Gem"]))
for (i,style) in enumerate((:core,:earth,:gem))
    scatter!(ax2,1:6,fill(i,6);color=Huevat.categorical(6;style),markersize=18)
end
save(joinpath(output,"makie.png"),fig)

settings=Huevat.plots(g;limits=(-2.,8.),center=0.)
@test settings.clims == (-2.,8.)
c=settings.c[0.2] # zero is 20% of the physical -2..8 range
@test maximum(abs.([red(c),green(c),blue(c)].-[red(at(g,.5)),green(at(g,.5)),blue(at(g,.5))])) < 1e-12
p=Plots.heatmap(z';settings...,title="Plots · centered at zero",size=(650,400))
Plots.savefig(p,joinpath(output,"plots.png"))
@testset "Native adapter interpolation" begin
    for name in (:sequential,:diverging,:multihue,:spectral,:cyclic)
        source=Huevat.gradient(name)
        native=Huevat.plots(source;limits=(-2.,8.),center=name in (:diverging,:spectral) ? 0. : nothing)
        for t in range(0,1;length=2049)
            x=Huevat.denormalize(t,-2.,8.,name in (:diverging,:spectral) ? 0. : nothing)
            color=native.c[(x+2)/10];expected=Huevat.at(source,t)
            @test maximum(abs.([red(color),green(color),blue(color)].-[red(expected),green(expected),blue(expected)])) < 2e-4
        end
    end
end
println("Rendered Makie and Plots figures; asymmetric center tests passed")
