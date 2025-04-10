import os
import json
import logging
from flask import current_app

def run_agent_with_openai(system_message, user_message, model=None):
    """
    Run an agent with OpenAI API
    
    Args:
        system_message (str): The system message that sets agent behavior
        user_message (str): The user message/query
        model (str): Optional model override
    
    Returns:
        str: The agent's response content
    """
    try:
        # Get API key from app config or environment
        api_key = current_app.config.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        
        if not api_key:
            logging.error("OpenAI API key not found in environment or app config")
            return "Error: OpenAI API key not found. Please add your API key to the .env file."
        
        # Use model from config if not specified
        if not model:
            model = current_app.config.get('OPENAI_MODEL') or 'gpt-4o'
            
        logging.info(f"Using OpenAI model: {model}")
        
        try:
            # Import here to avoid initial loading issues
            from openai import OpenAI
            
            # Initialize OpenAI client - make sure to not pass any unexpected params
            client = OpenAI(api_key=api_key)
            
            # Log request information (for debugging)
            logging.info(f"Making OpenAI API call with model: {model}")
            
            # Make API call
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # Extract and return the content
            if hasattr(response, 'choices') and response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            
            return "No response generated."
            
        except ImportError:
            # Fall back to older client if necessary
            logging.warning("Using alternative OpenAI client method")
            
            import openai
            openai.api_key = api_key
            
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # Extract and return the content
            if 'choices' in response and len(response['choices']) > 0:
                return response['choices'][0]['message']['content']
            
            return "No response generated."
    
    except Exception as e:
        # Log the error in production
        logging.error(f"Error calling OpenAI API: {str(e)}")
        
        # For development, include more details
        import traceback
        logging.error(traceback.format_exc())
        
        # Try a simpler alternative approach that's less likely to have compatibility issues
        try:
            logging.info("Attempting alternative API call approach")
            import openai
            openai.api_key = api_key
            
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
        except Exception as fallback_error:
            logging.error(f"Alternative approach also failed: {str(fallback_error)}")
            return f"Error generating content: {str(e)}"

# Alternative implementation using mock responses for testing without API
def run_agent_with_mock(system_message, user_message, role=None):
    """
    Run a mock agent for testing without API calls
    
    Args:
        system_message (str): The system message
        user_message (str): The user message
        role (str): Optional role to determine response template
    
    Returns:
        str: A mock response based on the role
    """
    logging.info(f"Using mock agent with role: {role}")
    
    if "brand_brief" in user_message.lower():
        return """
## Brand Brief
This company is a tech startup focused on developing AI-powered productivity tools for small businesses. Their target audience is small business owners and managers who need affordable, easy-to-use technology solutions. Their unique value proposition is providing enterprise-level AI capabilities at prices accessible to small businesses, with a focus on intuitive interfaces that require minimal training.

## Search Results Analysis
The search results indicate growing interest in AI solutions for small business productivity. Common topics include automation of routine tasks, data analysis for business insights, and customer service applications. Competitors are primarily focusing on specific niches like marketing automation or financial analysis, leaving an opportunity for comprehensive productivity solutions. Keywords frequently appearing include "small business AI", "affordable automation", and "productivity tools".
"""
    
    elif "content themes" in user_message.lower():
        return """
## Content Themes

1. **AI Basics for Small Business Owners**
   This theme focuses on introducing small business owners to fundamental AI concepts and applications relevant to their operations. It addresses the knowledge gap many small business owners face regarding AI technology while aligning with the brand's focus on accessible AI solutions.

2. **Productivity Automation Case Studies**
   This theme showcases real-world examples of how small businesses have successfully implemented automation to increase productivity. It demonstrates the practical value of the brand's offerings through relatable stories and measurable outcomes.

3. **Cost-Effective Technology Solutions**
   This theme explores how small businesses can leverage affordable technology to compete with larger companies. It directly addresses the target audience's pain point of limited budgets while highlighting the brand's value proposition of accessible pricing.

4. **Data-Driven Decision Making**
   This theme focuses on how small businesses can use data analytics to make better strategic decisions. It addresses the challenge many small businesses face in utilizing their data effectively and positions the brand as an enabler of data-driven insights.

5. **Customer Experience Enhancement**
   This theme explores how AI and automation can improve customer interactions and satisfaction. It addresses the audience's need to maintain quality customer relationships while scaling their business, showcasing the brand's customer-focused applications.

6. **Future-Proofing Small Businesses**
   This theme discusses how adopting AI and automation now can prepare small businesses for future technological changes and market shifts. It addresses the audience's concern about staying relevant and competitive in a rapidly evolving business landscape.
"""
    
    elif "content cluster" in user_message.lower():
        return """
## Content Cluster: Cost-Effective Technology Solutions

### Brand Alignment
This content cluster directly supports the brand's core value proposition of providing enterprise-level AI capabilities at prices accessible to small businesses. By focusing on cost-effective technology solutions, we can showcase how our intuitive, affordable tools help small businesses maximize their technology investment while competing with larger companies.

### Pillar Topic 1: ROI of AI for Small Businesses
- **Primary Search Intent**: Informational
- **Target Audience**: Budget-conscious small business owners
- **Strategic Value**: Establishing thought leadership and addressing purchase objections

#### Supporting Subtopics:
1. Calculating the true cost of manual processes vs. automation
2. How to measure productivity gains from AI implementation
3. Timeline for seeing ROI on various AI investments

### Pillar Topic 2: Budget-Friendly Tech Stack Essentials
- **Primary Search Intent**: Informational/Transactional
- **Target Audience**: Small business owners in growth phase
- **Strategic Value**: SEO for purchase-intent keywords and solution comparison

#### Supporting Subtopics:
1. Essential productivity tools every small business needs
2. Free and low-cost alternatives to enterprise software
3. Building an integrated tech stack without IT expertise

### Pillar Topic 3: Scaling Technology as You Grow
- **Primary Search Intent**: Informational
- **Target Audience**: Established small businesses looking to expand
- **Strategic Value**: Lead nurturing and customer retention

#### Supporting Subtopics:
1. When to upgrade your technology solutions
2. Avoiding common scaling pitfalls and unnecessary expenses
3. Future-proofing your technology investments
"""
    
    elif "article ideas" in user_message.lower():
        return """
## Content Ideas: Cost-Effective Technology Solutions

### Pillar Article: "The Small Business Guide to AI ROI: When and Where to Invest"
- **Target Keyword**: small business AI ROI
- **Word Count**: 2,500 words
- **Article Type**: Comprehensive Guide
- **Description**: This in-depth guide helps small business owners understand how to evaluate potential AI investments based on expected returns. It includes frameworks for calculating ROI, timelines for different types of AI implementations, and case studies showing real-world results from businesses of different sizes.

### Supporting Articles:

1. **"10 Hidden Costs of Manual Processes Eating Your Profits"**
   - **Target Keyword**: manual process costs business
   - **Description**: This article reveals the often-overlooked expenses associated with maintaining manual processes, including opportunity costs, error rates, and employee satisfaction impacts.

2. **"How to Measure Productivity Gains: Metrics That Matter for Small Businesses"**
   - **Target Keyword**: measure business productivity gains
   - **Description**: A practical guide to establishing baseline metrics and tracking improvements after implementing automation, with free templates and tools for businesses without dedicated analysts.

3. **"90-Day AI Implementation Plan: From Purchase to Payoff"**
   - **Target Keyword**: AI implementation timeline small business
   - **Description**: A step-by-step timeline showing how small businesses can implement AI solutions with minimal disruption and start seeing returns within three months.

### Pillar Article: "Building Your Small Business Tech Stack: Essential Tools That Won't Break the Bank"
- **Target Keyword**: small business essential tech stack
- **Word Count**: 2,000 words
- **Article Type**: List/Guide
- **Description**: A comprehensive overview of the fundamental technology solutions every small business needs, with budget-friendly options for each category. Includes recommendations for productivity suites, customer management, accounting, marketing automation, and AI assistants with price comparisons and integration considerations.

### Supporting Articles:

1. **"Free vs. Paid: When to Upgrade Your Business Software"**
   - **Target Keyword**: business software free vs paid
   - **Description**: An objective analysis of when free tools are sufficient and when it makes financial sense to invest in paid solutions, with decision frameworks for different business stages.

2. **"5 Enterprise-Level AI Tools with Small Business Pricing Options"**
   - **Target Keyword**: affordable enterprise AI tools
   - **Description**: Reviews of powerful AI platforms that offer scaled-down pricing for small businesses while maintaining core functionality.

3. **"The Non-Technical Owner's Guide to Integrating Business Software"**
   - **Target Keyword**: integrate business software without IT
   - **Description**: Step-by-step instructions for connecting various business applications without technical expertise, focusing on user-friendly integration platforms and no-code solutions.

### Pillar Article: "Technology That Grows With You: Smart Scaling for Small Businesses"
- **Target Keyword**: scale technology small business
- **Word Count**: 1,800 words
- **Article Type**: Strategic Guide
- **Description**: This forward-looking guide helps business owners make technology decisions that accommodate future growth. It covers modular systems that allow for incremental expansion, subscription models that scale with usage, and how to avoid technology that creates bottlenecks as your business expands.

### Supporting Articles:

1. **"Technology Upgrade Timeline: When to Revisit Your Tools"**
   - **Target Keyword**: when to upgrade business technology
   - **Description**: A framework for evaluating when your current technology is becoming a limitation rather than an asset, with warning signs that it's time to upgrade.

2. **"The True Cost of Outdated Technology: Beyond the Price Tag"**
   - **Target Keyword**: cost of outdated business technology
   - **Description**: An exploration of how outdated systems impact customer experience, employee satisfaction, and competitive positioning, even when they seem to be "working fine."

3. **"Future-Proof Tech Investments: Choosing Technology That Lasts"**
   - **Target Keyword**: future-proof business technology
   - **Description**: Guidance on evaluating the longevity of technology investments, including compatibility standards, vendor stability, and industry adoption trends.
"""
    
    elif "final content plan" in user_message.lower():
        return """
# Final Content Plan

## Executive Summary
This content plan focuses on "Cost-Effective Technology Solutions" as the primary theme, directly addressing the needs of budget-conscious small business owners while showcasing the brand's value proposition of affordable AI tools. The strategy targets high-intent keywords related to business productivity, ROI, and technology implementation, creating a comprehensive resource that guides prospects through awareness, consideration, and decision stages. By demonstrating thought leadership in accessible AI solutions, this content cluster will position the brand as the go-to expert for small businesses looking to leverage technology without enterprise-level budgets.

## Brand Brief
This company is a tech startup focused on developing AI-powered productivity tools for small businesses. Their target audience is small business owners and managers who need affordable, easy-to-use technology solutions. Their unique value proposition is providing enterprise-level AI capabilities at prices accessible to small businesses, with a focus on intuitive interfaces that require minimal training. The brand voice is knowledgeable but approachable, practical rather than technical, and empowering to small business owners who may feel intimidated by advanced technology.

## Selected Theme: Cost-Effective Technology Solutions
This theme directly aligns with both audience needs and business objectives by addressing the primary barrier to AI adoption among small businesses: perceived high costs and unclear returns. By focusing on the cost-effectiveness and practical ROI of AI solutions, we can overcome purchase objections while highlighting the brand's core differentiation from enterprise-focused competitors. This theme also has strong search potential with clear purchase intent keywords and limited high-quality content from competitors.

## Content Cluster Structure

### Pillar Topic 1: ROI of AI for Small Businesses
- **Primary Search Intent**: Informational
- **Target Audience**: Budget-conscious small business owners
- **Strategic Value**: Establishing thought leadership and addressing purchase objections

#### Supporting Subtopics:
1. Calculating the true cost of manual processes vs. automation
2. How to measure productivity gains from AI implementation
3. Timeline for seeing ROI on various AI investments

### Pillar Topic 2: Budget-Friendly Tech Stack Essentials
- **Primary Search Intent**: Informational/Transactional
- **Target Audience**: Small business owners in growth phase
- **Strategic Value**: SEO for purchase-intent keywords and solution comparison

#### Supporting Subtopics:
1. Essential productivity tools every small business needs
2. Free and low-cost alternatives to enterprise software
3. Building an integrated tech stack without IT expertise

### Pillar Topic 3: Scaling Technology as You Grow
- **Primary Search Intent**: Informational
- **Target Audience**: Established small businesses looking to expand
- **Strategic Value**: Lead nurturing and customer retention

#### Supporting Subtopics:
1. When to upgrade your technology solutions
2. Avoiding common scaling pitfalls and unnecessary expenses
3. Future-proofing your technology investments

## Article Recommendations

### Pillar Article 1: "The Small Business Guide to AI ROI: When and Where to Invest"
- **Target Keyword**: small business AI ROI
- **Word Count**: 2,500 words
- **Article Type**: Comprehensive Guide
- **Description**: This in-depth guide helps small business owners understand how to evaluate potential AI investments based on expected returns. It includes frameworks for calculating ROI, timelines for different types of AI implementations, and case studies showing real-world results from businesses of different sizes.

#### Supporting Articles:
1. **"10 Hidden Costs of Manual Processes Eating Your Profits"**
2. **"How to Measure Productivity Gains: Metrics That Matter for Small Businesses"**
3. **"90-Day AI Implementation Plan: From Purchase to Payoff"**

### Pillar Article 2: "Building Your Small Business Tech Stack: Essential Tools That Won't Break the Bank"
- **Target Keyword**: small business essential tech stack
- **Word Count**: 2,000 words
- **Article Type**: List/Guide
- **Description**: A comprehensive overview of the fundamental technology solutions every small business needs, with budget-friendly options for each category. Includes recommendations for productivity suites, customer management, accounting, marketing automation, and AI assistants with price comparisons and integration considerations.

#### Supporting Articles:
1. **"Free vs. Paid: When to Upgrade Your Business Software"**
2. **"5 Enterprise-Level AI Tools with Small Business Pricing Options"**
3. **"The Non-Technical Owner's Guide to Integrating Business Software"**

### Pillar Article 3: "Technology That Grows With You: Smart Scaling for Small Businesses"
- **Target Keyword**: scale technology small business
- **Word Count**: 1,800 words
- **Article Type**: Strategic Guide
- **Description**: This forward-looking guide helps business owners make technology decisions that accommodate future growth. It covers modular systems that allow for incremental expansion, subscription models that scale with usage, and how to avoid technology that creates bottlenecks as your business expands.

#### Supporting Articles:
1. **"Technology Upgrade Timeline: When to Revisit Your Tools"**
2. **"The True Cost of Outdated Technology: Beyond the Price Tag"**
3. **"Future-Proof Tech Investments: Choosing Technology That Lasts"**

## Implementation Guidelines
- **Recommended Publishing Cadence**: 1 article per week, starting with pillar articles (one per month) followed by supporting articles (weekly)
- **Content Distribution Channels**: Company blog, LinkedIn, Email newsletter, Guest posts on small business publications
- **Success Metrics**: Organic traffic growth, keyword rankings, lead magnet downloads, demo requests from organic blog visitors
- **Additional Considerations**: Create downloadable templates for ROI calculations, technology assessment worksheets, and implementation checklists as lead magnets for each pillar topic

## Next Steps
- Develop detailed outlines for each pillar article with section breakdowns
- Create a publishing calendar with specific dates for each piece
- Design custom graphics and interactive elements for the pillar content
- Identify potential case studies and reach out to featured businesses
- Develop lead magnets and conversion points for each content piece
"""
    
    else:
        # Default mock response
        return "This is a mock response for testing. In production, this would call the OpenAI API."
