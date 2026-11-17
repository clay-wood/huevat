module Huevat
import Colors
using Colors: RGB, Colorant, red, green, blue
import JSON
using SHA: sha256
include("checksum.jl")

export categorical, categorical_names, gradient, gradient_names, at, discrete,
       known_counts, colormap, color_map, makie, plots, normalize, denormalize

const DATA = Ref{Any}(nothing)
function data()
    DATA[] !== nothing && return DATA[]
    raw=replace(read(joinpath(@__DIR__, "..", "data", "palettes.json"),String),"\r\n"=>"\n")
    bytes2hex(sha256(raw)) == DATA_SHA256 || error("Huevat color resource checksum mismatch")
    parsed=JSON.parse(raw)
    parsed["version"] == "h5-julia-v1" || error("Unknown Huevat color resource")
    DATA[]=parsed
end
categorical_names() = (:core, :earth, :gem, Symbol("max-separation"))
function categorical(n::Integer; style=:core, background=:light)
    n isa Bool && throw(ArgumentError("n must be an integer count"))
    style = string(style) == "clearer" ? "core" : string(style)
    key = "$style/$background/$n"
    haskey(data()["categorical"], key) || throw(ArgumentError("No checked palette for $key"))
    return parse.(RGB{Float64}, data()["categorical"][key])
end
function color_map(colors, labels)
    length(colors) == length(labels) || throw(ArgumentError("One label per color is required"))
    length(unique(labels)) == length(labels) || throw(ArgumentError("Labels must be unique"))
    Dict(zip(labels, colors))
end

struct Gradient
    recipe::Dict{String,Any}
    reversed::Bool
    counts::Dict{String,Any}
end
function gradient(name=:sequential; background=nothing)
    route=string(name);dark=false;reversed=false
    while endswith(route,"_d") || endswith(route,"_r")
        if endswith(route,"_d")
            dark && throw(ArgumentError("Duplicate dark suffix"));dark=true
        else
            reversed && throw(ArgumentError("Duplicate reverse suffix"));reversed=true
        end
        route=route[1:end-2]
    end
    dark && background !== nothing && string(background)!="dark" && throw(ArgumentError("Dark suffix conflicts with background"))
    bg=dark ? "dark" : background === nothing ? "light" : string(background)
    key = "$route/$bg"
    haskey(data()["gradients"],key) || throw(ArgumentError("Unknown gradient: $key"))
    g = data()["gradients"][key]
    Gradient(deepcopy(Dict{String,Any}(g["recipe"])),xor(g["reversed"],reversed),deepcopy(Dict{String,Any}(g["counts"])))
end
gradient_names() = sort!(unique(first(split(k,"/")) for k in keys(data()["gradients"])))
Base.reverse(g::Gradient) = Gradient(deepcopy(g.recipe),!g.reversed,deepcopy(g.counts))
function at(g::Gradient, t::Real)
    t isa Bool && throw(ArgumentError("Position must be numeric"))
    isfinite(t) && 0 <= t <= 1 || throw(ArgumentError("Position must be in [0,1]"))
    if g.recipe["family"] == "cyclic" && t == 1
        t=0
    end
    t = g.reversed ? 1-t : t
    knots = g.recipe["knots"]
    i = min(findfirst(k -> t <= k, knots[2:end]),length(knots)-1)
    u = (t-knots[i])/(knots[i+1]-knots[i])
    L,a,b = [((c[4]*u+c[3])*u+c[2])*u+c[1] for c in g.recipe["segments"][i]]
    l,m,s = (L+0.3963377774a+0.2158037573b)^3, (L-0.1055613458a-0.0638541728b)^3, (L-0.0894841775a-1.2914855480b)^3
    linear = (4.0767416621l-3.3077115913m+0.2309699292s,
              -1.2684380046l+2.6097574011m-0.3413193965s,
              -0.0041960863l-0.7034186147m+1.7076147010s)
    encode(x) = x <= 0.0031308 ? 12.92x : 1.055*x^(1/2.4)-0.055
    rgb = encode.(linear)
    all(x -> -1e-7 <= x <= 1+1e-7,rgb) || throw(ArgumentError("Gradient left sRGB gamut"))
    RGB{Float64}(clamp.(rgb,0,1)...)
end
function known_counts(g::Gradient; context="filled-fields")
    sort!([parse(Int,last(split(k,"/"))) for k in keys(g.counts) if startswith(k,"$context/")])
end
function discrete(g::Gradient,n::Integer; context="filled-fields")
    n isa Bool && throw(ArgumentError("n must be a count"))
    key = "$context/$n"
    haskey(g.counts,key) || throw(ArgumentError("Count is not prepared; checked counts: $(known_counts(g;context))"))
    colors = parse.(RGB{Float64},g.counts[key])
    if g.reversed && g.recipe["family"] == "cyclic"
        return [first(colors); reverse(colors[2:end])]
    end
    g.reversed ? reverse(colors) : colors
end
function colormap(g::Gradient; n=1025)
    n isa Integer && !(n isa Bool) && n >= 3 || throw(ArgumentError("n must be an integer of at least 3"))
    at.(Ref(g),range(0,1;length=n))
end
function limits(lo,hi,center)
    all(isfinite,(lo,hi)) && lo < hi || throw(ArgumentError("Limits must be finite and increasing"))
    center === nothing || (isfinite(center) && lo < center < hi) || throw(ArgumentError("Center must be inside limits"))
    nothing
end
function normalize(x,lo,hi,center=nothing)
    limits(lo,hi,center)
    center === nothing ? (x-lo)/(hi-lo) : x <= center ? 0.5*(x-lo)/(center-lo) : 0.5+0.5*(x-center)/(hi-center)
end
function denormalize(t,lo,hi,center=nothing)
    limits(lo,hi,center)
    center === nothing ? lo+t*(hi-lo) : t <= 0.5 ? lo+2t*(center-lo) : center+2(t-0.5)*(hi-center)
end
function makie end
function plots end
end
