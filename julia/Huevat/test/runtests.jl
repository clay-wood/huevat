using Test, Huevat
using Huevat.Colors: red, green, blue
using Huevat.Colors: RGB
import Huevat.JSON as JSON

@testset "Python/Julia colors and normalization" begin
    @test categorical(6;style=:core) == categorical(6;style=:clearer)
    @test length(categorical(8;style=:earth,background=:dark)) == 8
    @test length(categorical(8;style=:gem)) == 8
    @test_throws ArgumentError categorical(true)
    @test at(gradient(:thermal_d_r),.2)==at(reverse(gradient(:thermal;background=:dark)),.2)
    @test_throws ArgumentError gradient(:thermal_d;background=:light)
    @test_throws ArgumentError color_map(categorical(2),["A","A"])
    @test Huevat.normalize(0.,-2.,8.,0.) == 0.5
    @test Huevat.denormalize(0.5,-2.,8.,0.) == 0.
    @test Huevat.normalize(-2.,-2.,8.,0.) == 0.
    @test Huevat.normalize(8.,-2.,8.,0.) == 1.
    @test_throws ArgumentError Huevat.normalize(0.,-2.,8.,9.)
    for (key, samples) in JSON.parsefile(joinpath(@__DIR__,"reference.json"))
        name,bg=split(key,"/");g=gradient(name;background=bg)
        for (i,rgb) in enumerate(samples)
            c=at(g,(i-1)/64)
            @test maximum(abs.([red(c),green(c),blue(c)].-rgb)) < 2e-12
        end
        @test at(reverse(g),0.25) == at(g,0.75)
        for n in known_counts(g)
            @test length(discrete(g,n))==n
        end
    end
    for (key,counts) in JSON.parsefile(joinpath(@__DIR__,"counts.json"))
        name,bg=split(key,"/");g=gradient(name;background=bg)
        for (spec,hex) in counts
            context,count=split(spec,"/");n=parse(Int,count)
            @test discrete(g,n;context) == parse.(RGB{Float64},hex)
        end
    end
    g=gradient(:cyclic)
    @test at(g,0)==at(g,1)
    @test at(reverse(g),0)==at(reverse(g),1)
    @test first(discrete(reverse(g),4))==first(discrete(g,4))
    old=at(gradient(:diverging),.2)
    g=gradient(:diverging);g.recipe["segments"][1][1][1]=99
    @test at(gradient(:diverging),.2)==old
end
