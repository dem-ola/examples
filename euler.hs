--- Solutions to Project Euler: https://projecteuler.net/archives

import Data.List

-- test from half-way down as all > half will be null
isPrime :: (Integral a) => a -> Bool
isPrime lim | mod lim 2 == 0 = False  
            | null [ p | p <- [2..a], mod lim p == 0 ] = True
            | otherwise = False
            where a = div lim 2

-- all primes
primes :: [Integer]
primes = [ p | p <- [2..], isPrime p]

-- all primes up to and uncluding limit note: sorted reverse
primesTo :: Integral a => a -> [a]
primesTo lim = [ p | p <- [lim,lim-1..2], isPrime p]

-- get prime factors :: 
primeFactors :: Integral a => a -> [a]
primeFactors lim = go lim [] 2
         where 
         go lim factors p 
             | divvy == 1 = [lim] 
             | isPrime p && mod lim p == 0 = p:go divvy factors p
             | otherwise = go lim factors (p+1)
             where divvy = div lim p


-- highest prime number up to a number
-- takes a looooong time e.g. 
-- lim 1000000000 (i.e. 1 billion) -> 3 mins+ ......
-- lim 100000000 -> 150 secs
-- lim 10000000 -> 10-15 secs
-- lim 1000000 -> 3 secs
-- faster with first of the reversed primesTo func than last of primes func
highPrime :: Integral a => a -> [a]
highPrime lim = take 1 $ primesTo lim

-- fibonacci 30 -> 8-10s
fibonacci :: [Integer]
fibonacci = 0 : scanl (+) 1 fibonacci

-- note: zero based index
fibth :: Int -> Integer
fibth n = fibonacci !! n

-- returns sequence of n items: nb fib 0 = 1 by defn thus n+1 below
fib :: Int -> [Integer]
fib n = take (n+1) fibonacci

-- split strings into chars in list
splitStr :: String -> [[Char]]
splitStr str = map (:[]) str

-- convert string eg "123" to integer; nb error if arg is not string
readInt :: String -> Integer
readInt r = read r :: Integer


-- ================== ^^^ HELPER FUNCTIONS ^^^ ==================

-- sum of numbers below limit divisible by 2 other numbers
-- [1000 3 5] ::
euler1 :: Integral a => a -> a -> a -> a
euler1 limit a b = sum [ x | x <- [1..limit-1], mod x a == 0 || mod x b == 0 ]

-- sum even valued fibonacci numbers <= arg
euler2 :: Integer -> Integer
euler2 lim = sum $ filter even $ takeWhile (<=lim) fibonacci


-- highest prime factor :: 600851475143
-- much faster to use primeFactors than call primes and test for factors
-- lim 100000000 -> <01s b/c primeFactors recursively divides lim 
-- lim 123456789 -> 1 sec
-- lim 600851475 -- 50 secs :: so depends on no of primes & recursive divides
-- lim 600851475143 -> 1-2 secs
euler3 :: Integral a => a -> a
euler3 lim = last $ primeFactors lim


-- [999 x 999] :: highest prod of two 3 digit numbs that's a palindrome
euler4 :: (Ord a, Num a, Enum a, Show a) => a -> a -> (a,a,a)
euler4 a b = last $ sort [ (x*y,x,y) | x <- [1..a]
                         , y <- [1..b]
                         , show (x * y) == reverse ( show (x * y)) ]


-- smallest multiple of numbers up to arg
-- [20] :: don't run as 10mins and counting -> try 16; 17 -> 60s ish
euler5 :: Integral a => a -> a
euler5 lim = go lim 2
    where 
    go lim possible
        | all (==0) $ map (mod possible) [2..lim] = possible
        | possible == foldl1 (*) [1..lim] = 0
        | otherwise = go lim (possible+1)


-- [100] :: diff btw sum of squares and square of sum
euler6 :: (Num a, Enum a) => a -> a
euler6 lim = abs $ ((^2) $ sum [1..lim]) - sum [x^2 | x <- [1..lim]]

-- [10001] :: nth prime :: T:> 4000 -> 45s, 10000 -> 12mins
euler7 :: Int -> Integer
euler7 e = primes !! e

-- for euler 8
-- # highest product of n successive numbers
huge = 7316717653133062491922511967442657474235534919493496983520312774506326239578318016984801869478851843858615607891129494954595017379583319528532088055111254069874715852386305071569329096329522744304355766896648950445244523161731856403098711121722383113622298934233803081353362766142828064444866452387493035890729629049156044077239071381051585930796086670172427121883998797908792274921901699720888093776657273330010533678812202354218097512545405947522435258490771167055601360483958644670632441572215539753697817977846174064955149290862569321978468622482839722413756570560574902614079729686524145351004748216637048440319989000889524345065854122758866688116427171479924442928230863465674813919123162824586178664583591245665294765456828489128831426076900422421902267105562632111110937054421750694165896040807198403850962455444362981230987879927244284909188845801561660979191338754992005240636899125607176060588611646710940507754100225698315520005593572972571636269561882670428252483600823257530420752963450

euler8 :: Show a => a -> Int -> (Integer, [Integer])
euler8 numb e = go numb e 0 [] 0
     where
     go numb e record digits cursor
         | length token < e = (record, map readInt digits)
         | prod > record = go numb e prod token (cursor+1)
         | otherwise = go numb e record digits (cursor+1)
         where prod = product $ map readInt token
               token = (splitStr ( take e $ stringed ))
               stringed = drop cursor $ show numb

-- 1000 :: right-angle triangle where a + b + c == lim;
-- time depends on if answer exsts /w ans lim 1000 T:> 35s; w/o ans 500 T:> 55s
euler9 :: (Enum a, Eq a, Integral a) => a -> [(a, a, a)] 
euler9 lim = take 1 [(a, b, hyp) | hyp <- [1..lim], a <- [1..hyp]
                                , b <- [1..a], a^2 + b^2 == hyp^2
                                , a + b + hyp == lim ]


-- sum of all the primes below n
euler12 :: Integer -> Integer
euler12 n = sum $ takeWhile (<n) [x | x <- primes]