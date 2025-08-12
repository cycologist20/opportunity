"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Clock, Zap, HelpCircle, Target, Brain, FileText, Check, Menu, X } from "lucide-react"
import Image from "next/image"
import Link from "next/link"

export default function OpportunityKnocksLanding() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#1A1A1A] text-[#F5F5F5]">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-[#1A1A1A]/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Image
                src="/logo.png"
                alt="Opportunity Knocks AI"
                width={240}
                height={48}
                className="h-10 w-auto"
                priority
              />
            </div>

            <div className="hidden md:block">
              <Button className="bg-[#39FF14] text-black hover:bg-[#39FF14]/90 font-semibold px-6" asChild>
                <Link href="#pricing">Get Your Brief</Link>
              </Button>
            </div>

            <div className="md:hidden">
              <Button variant="ghost" size="sm" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
                {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </Button>
            </div>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden bg-[#1A1A1A] border-t border-gray-800">
            <div className="px-4 py-4">
              <Button className="bg-[#39FF14] text-black hover:bg-[#39FF14]/90 font-semibold w-full" asChild>
                <Link href="#pricing">Get Your Brief</Link>
              </Button>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 opacity-10">
          <svg className="w-full h-full" viewBox="0 0 1200 800">
            <defs>
              <linearGradient id="pathGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#39FF14" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#39FF14" stopOpacity="0.8" />
              </linearGradient>
            </defs>
            {/* Chaotic lines that resolve into straight path */}
            <path
              d="M0,400 Q100,200 200,400 T400,300 Q500,500 600,400 T800,350 Q900,250 1000,400 L1200,400"
              stroke="url(#pathGradient)"
              strokeWidth="3"
              fill="none"
              className="animate-pulse"
            />
            <path
              d="M0,450 Q150,150 300,450 T600,250 Q700,600 800,450 T1000,300 L1200,450"
              stroke="url(#pathGradient)"
              strokeWidth="2"
              fill="none"
              className="animate-pulse"
              style={{ animationDelay: "1s" }}
            />
            <path
              d="M200,400 L1000,400"
              stroke="#39FF14"
              strokeWidth="4"
              fill="none"
              className="animate-pulse"
              style={{ animationDelay: "2s" }}
            />
          </svg>
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Stop Searching.
            <br />
            <span className="text-[#39FF14]">Start Building.</span>
          </h1>

          <h2 className="text-xl md:text-2xl mb-8 text-gray-300 max-w-3xl mx-auto leading-relaxed">
            We analyze thousands of hours of content from YouTube videos and academic papers to find your next great
            business idea.
          </h2>

          <Button
            size="lg"
            className="bg-[#39FF14] text-black hover:bg-[#39FF14]/90 font-bold text-lg px-8 py-4 h-auto"
            asChild
          >
            <Link href="#pricing">Get Your Opportunity Brief Now</Link>
          </Button>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-20 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold text-center mb-16">
            Endless Research is a <span className="text-[#39FF14]">Dead End</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#39FF14]/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Clock className="w-8 h-8 text-[#39FF14]" />
              </div>
              <h3 className="text-xl font-bold mb-4">Wasted Hours</h3>
              <p className="text-gray-300">Stop losing weeks to manual research and content rabbit holes.</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-[#39FF14]/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Zap className="w-8 h-8 text-[#39FF14]" />
              </div>
              <h3 className="text-xl font-bold mb-4">Information Overload</h3>
              <p className="text-gray-300">Cut through the noise and get a clear, actionable signal.</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-[#39FF14]/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <HelpCircle className="w-8 h-8 text-[#39FF14]" />
              </div>
              <h3 className="text-xl font-bold mb-4">Paralyzing Uncertainty</h3>
              <p className="text-gray-300">Move forward with a data-backed idea you can trust.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-20 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold text-center mb-16">
            Your Path to <span className="text-[#39FF14]">Clarity</span> in 3 Steps
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#39FF14] rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-black font-bold text-xl">1</span>
              </div>
              <div className="w-12 h-12 bg-[#39FF14]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Target className="w-6 h-6 text-[#39FF14]" />
              </div>
              <h3 className="text-xl font-bold mb-4">Tell Us Your Interests</h3>
              <p className="text-gray-300">You provide the topic, industry, or questions you want to explore.</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-[#39FF14] rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-black font-bold text-xl">2</span>
              </div>
              <div className="w-12 h-12 bg-[#39FF14]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Brain className="w-6 h-6 text-[#39FF14]" />
              </div>
              <h3 className="text-xl font-bold mb-4">Our AI Synthesizes the Data</h3>
              <p className="text-gray-300">Our toolkit analyzes thousands of sources for patterns and opportunities.</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-[#39FF14] rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-black font-bold text-xl">3</span>
              </div>
              <div className="w-12 h-12 bg-[#39FF14]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="w-6 h-6 text-[#39FF14]" />
              </div>
              <h3 className="text-xl font-bold mb-4">Receive Your Opportunity Brief</h3>
              <p className="text-gray-300">Get a comprehensive, easy-to-read report delivered to your inbox.</p>
            </div>
          </div>
        </div>
      </section>

      {/* What You Get Section */}
      <section className="py-20 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold text-center mb-16">
            The Opportunity Brief: Your <span className="text-[#39FF14]">Unfair Advantage</span>
          </h2>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="order-2 lg:order-1">
              <Image
                src="/placeholder-sufbx.png"
                alt="Opportunity Brief Report Mockup"
                width={500}
                height={600}
                className="w-full max-w-md mx-auto"
              />
            </div>

            <div className="order-1 lg:order-2">
              <ul className="space-y-6">
                <li className="flex items-start">
                  <Check className="w-6 h-6 text-[#39FF14] mr-4 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-bold mb-2">In-depth Market Analysis</h3>
                    <p className="text-gray-300">Comprehensive market research and competitive landscape analysis.</p>
                  </div>
                </li>

                <li className="flex items-start">
                  <Check className="w-6 h-6 text-[#39FF14] mr-4 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-bold mb-2">Key Trends & Patterns</h3>
                    <p className="text-gray-300">
                      Emerging trends and patterns identified from thousands of data sources.
                    </p>
                  </div>
                </li>

                <li className="flex items-start">
                  <Check className="w-6 h-6 text-[#39FF14] mr-4 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-bold mb-2">Synthesized Business Models</h3>
                    <p className="text-gray-300">Proven business models tailored to your opportunity.</p>
                  </div>
                </li>

                <li className="flex items-start">
                  <Check className="w-6 h-6 text-[#39FF14] mr-4 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-bold mb-2">Target Customer Personas</h3>
                    <p className="text-gray-300">Detailed profiles of your ideal customers and their pain points.</p>
                  </div>
                </li>

                <li className="flex items-start">
                  <Check className="w-6 h-6 text-[#39FF14] mr-4 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-bold mb-2">Actionable First Steps</h3>
                    <p className="text-gray-300">Clear, concrete actions you can take immediately to get started.</p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-gray-900/50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Card className="bg-[#1A1A1A] border-[#39FF14] border-2 p-8">
            <CardContent className="p-0">
              <h2 className="text-3xl md:text-4xl font-bold mb-4 text-[#F5F5F5]">Get Your Opportunity Brief</h2>
              <div className="text-6xl font-bold text-[#39FF14] mb-4">$99</div>
              <p className="text-xl text-gray-300 mb-8">A one-time purchase. No subscriptions.</p>

              <Button
                size="lg"
                className="bg-[#39FF14] text-black hover:bg-[#39FF14]/90 font-bold text-xl px-12 py-6 h-auto w-full md:w-auto"
                asChild
              >
                <Link href="https://buy.stripe.com/your-payment-link">Unlock Your Opportunity Now</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 bg-[#1A1A1A]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold text-center mb-16">
            Frequently Asked <span className="text-[#39FF14]">Questions</span>
          </h2>

          <Accordion type="single" collapsible className="space-y-4">
            <AccordionItem value="sources" className="border-gray-700">
              <AccordionTrigger className="text-left text-lg font-semibold hover:text-[#39FF14]">
                What sources do you analyze?
              </AccordionTrigger>
              <AccordionContent className="text-gray-300 text-base">
                We analyze thousands of hours of content from YouTube videos, academic papers, industry reports, market
                research, and trending business publications. Our AI processes this vast amount of information to
                identify patterns, opportunities, and emerging trends that humans might miss.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="audience" className="border-gray-700">
              <AccordionTrigger className="text-left text-lg font-semibold hover:text-[#39FF14]">
                Who is this service for?
              </AccordionTrigger>
              <AccordionContent className="text-gray-300 text-base">
                This service is perfect for entrepreneurs, business professionals, consultants, and anyone looking to
                identify new business opportunities. Whether you're a seasoned entrepreneur or just starting out, our
                AI-powered analysis helps you discover data-backed business ideas in any industry or niche.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="timeline" className="border-gray-700">
              <AccordionTrigger className="text-left text-lg font-semibold hover:text-[#39FF14]">
                How long does it take to get my report?
              </AccordionTrigger>
              <AccordionContent className="text-gray-300 text-base">
                Your comprehensive Opportunity Brief will be delivered to your inbox within 48-72 hours of purchase. Our
                AI needs time to thoroughly analyze thousands of sources and synthesize the findings into actionable
                insights tailored to your specific interests and requirements.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="guarantee" className="border-gray-700">
              <AccordionTrigger className="text-left text-lg font-semibold hover:text-[#39FF14]">
                What if I don't like the ideas in my report?
              </AccordionTrigger>
              <AccordionContent className="text-gray-300 text-base">
                We're confident in the quality and value of our analysis. However, if you're not satisfied with your
                Opportunity Brief, we offer a 30-day money-back guarantee. Simply contact our support team, and we'll
                process your refund promptly, no questions asked.
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <Image src="/logo.png" alt="Opportunity Knocks AI" width={240} height={48} className="h-10 w-auto" />
            </div>

            <div className="text-center md:text-right">
              <p className="text-gray-400 mb-2">Copyright © 2025 Opportunity Knocks AI. All rights reserved.</p>
              <div className="space-x-4">
                <Link href="/terms" className="text-gray-400 hover:text-[#39FF14] text-sm">
                  Terms of Service
                </Link>
                <Link href="/privacy" className="text-gray-400 hover:text-[#39FF14] text-sm">
                  Privacy Policy
                </Link>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
