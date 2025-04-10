from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect  # Only import CSRFProtect, not csrf
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, URL
import uuid
import json
import os
import re
from datetime import datetime
from config import get_config
from models import db, Job
from utils.scraper import scrape_website, validate_url
from utils.search import search_serpapi, deduplicate_results
from utils.workflow import WorkflowManager

app = Flask(__name__)
app.config.from_object(get_config())

# Initialize the configuration with the app
get_config().init_app(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# Forms
class ContentWorkflowForm(FlaskForm):
    website_url = StringField('Website URL', validators=[DataRequired(), URL()])
    keywords = TextAreaField('Search Keywords (one per line or comma-separated)', validators=[DataRequired()])

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ContentWorkflowForm()
    
    # Debug information
    app.logger.info(f"Method: {request.method}")
    if request.method == 'POST':
        app.logger.info(f"Form data: {request.form}")
        app.logger.info(f"Form validation: {form.validate()}")
        if form.errors:
            app.logger.info(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        app.logger.info("Form validated successfully")
        
        try:
            # Create a unique job ID
            job_id = str(uuid.uuid4())
            
            # Create new job in database
            job = Job(
                job_id=job_id,
                website_url=form.website_url.data,
                keywords=form.keywords.data
            )
            db.session.add(job)
            db.session.commit()
            
            # Start the workflow process
            process_workflow(job_id)
            
            return redirect(url_for('process_job', job_id=job_id))
            
        except Exception as e:
            app.logger.error(f"Error creating job: {str(e)}")
            flash('An error occurred while creating your job. Please try again.', 'error')
            return redirect(url_for('index'))
    else:
        if request.method == 'POST':
            app.logger.info("Form validation failed")
            flash("Please correct the errors in the form", "error")
    
    return render_template('index.html', form=form)

@app.route('/process/<job_id>', methods=['GET'])
def process_job(job_id):
    job = Job.get_by_id(job_id)
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('processing.html', job=job)

@app.route('/job-status/<job_id>', methods=['GET'])
def job_status(job_id):
    job = Job.get_by_id(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job.to_dict())

@app.route('/results/<job_id>', methods=['GET'])
def results(job_id):
    job = Job.get_by_id(job_id)
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('index'))
    
    if job.status != 'completed':
        return redirect(url_for('process_job', job_id=job_id))
    
    return render_template('results.html', job=job)

@app.route('/api/theme-selection/<job_id>', methods=['POST'])
@csrf.exempt
def theme_selection(job_id):
    job = Job.get_by_id(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        data = request.get_json()
        if not data or 'selected_themes' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        # Update workflow state with selected themes
        current_state = job.workflow_state or {}
        current_state['selected_themes'] = data['selected_themes']
        job.update_workflow_state(current_state)
        
        # Continue workflow
        continue_workflow_after_selection(job_id)
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        app.logger.error(f"Error in theme selection: {str(e)}")
        job.update_status('error', str(e))
        return jsonify({'error': str(e)}), 500

def process_workflow(job_id):
    """Process the content workflow for a job"""
    job = Job.get_by_id(job_id)
    
    try:
        # Step 1: Initialize workflow
        job.status = 'processing'
        job.progress = 0
        
        workflow_manager = WorkflowManager()
        job.workflow_state = workflow_manager.save_state()
        job.current_phase = workflow_manager.current_phase
        
        # Step 2: Scrape website
        job.messages.append(f"Retrieving content from {job.website_url}...")
        website_content = scrape_website(job.website_url)
        
        if website_content.startswith("Error"):
            job.status = 'error'
            job.error = website_content
            job.messages.append(website_content)
            return
        
        job.website_content_length = len(website_content)
        job.progress = 10
        job.messages.append(f"Retrieved {len(website_content)} characters of content")
        
        # Step 3: Search for keywords
        job.messages.append(f"Searching for keywords: {', '.join(job.keywords)}")
        all_search_results = []
        failed_keywords = []
        
        # Get API key from config
        serpapi_key = app.config.get('SERPAPI_API_KEY')
        
        for keyword in job.keywords:
            try:
                results = search_serpapi(keyword, serpapi_key)
                if results:
                    all_search_results.extend(results)
                else:
                    failed_keywords.append(keyword)
                    job.messages.append(f"No results found for keyword: {keyword}")
            except Exception as e:
                failed_keywords.append(keyword)
                job.messages.append(f"Error searching for '{keyword}': {str(e)}")
        
        # Deduplicate results
        unique_results = deduplicate_results(all_search_results)
        total_results = len(unique_results)
        
        if total_results == 0:
            job.status = 'error'
            job.error = "No search results were found for any keywords. Try different keywords."
            job.messages.append("No search results were found for any keywords. Try different keywords.")
            return
        
        job.search_results = unique_results
        job.search_results_count = total_results
        job.progress = 20
        job.messages.append(f"Found {total_results} unique search results after deduplication")
        
        # Step 4: Begin agent workflow
        job.messages.append("Starting content research workflow...")
        
        # Advance workflow to RESEARCH phase
        workflow_manager.advance_phase()  # To RESEARCH
        job.workflow_state = workflow_manager.save_state()
        job.current_phase = workflow_manager.current_phase
        
        # Research phase
        job.messages.append("RESEARCH PHASE: Analyzing website content and search results")
        from utils.agents import run_agent_with_openai
        
        system_message = """You are a research agent specialized in retrieving and summarizing content.
        
        Your specific responsibilities:
        1. Analyze website content to create a 'brand_brief' that summarizes:
           - What the business does
           - Their target audience
           - Their unique value proposition
           - Their brand voice/tone
        
        2. Process search results from keywords to identify relevant information.
           - Key topics and subtopics
           - Frequently used keywords and phrases (SEO)
           - Competitor topics
           - Potential content gaps
        
        FORMAT YOUR OUTPUT:
        
        ## Brand Brief
        [Provide a 200-300 word summary of the brand based on website content]
        
        ## Search Results Analysis
        [Provide a 200-300 word analysis of key insights from the search results]
        """
        
        user_message = f"""
        ## Website Content
        {website_content[:8000]}... (truncated)
        
        ## Search Results
        {json.dumps(unique_results[:10], indent=2)}
        
        Please analyze this content and provide the Brand Brief and Search Results Analysis.
        """
        
        try:
            response = run_agent_with_openai(system_message, user_message)
            
            # Parse the results
            brand_brief = ""
            search_analysis = ""
            
            if "## Brand Brief" in response:
                parts = response.split("## Brand Brief", 1)
                if len(parts) > 1:
                    remaining = parts[1]
                    if "## Search Results Analysis" in remaining:
                        brand_parts = remaining.split("## Search Results Analysis", 1)
                        brand_brief = brand_parts[0].strip()
                        search_analysis = brand_parts[1].strip()
                    else:
                        brand_brief = remaining.strip()
            
            job.brand_brief = brand_brief
            job.search_analysis = search_analysis
            job.progress = 40
            job.messages.append("Completed research phase with brand brief and search analysis")
            
            # Advance workflow to ANALYSIS phase
            workflow_manager.advance_phase()  # To ANALYSIS
            job.workflow_state = workflow_manager.save_state()
            job.current_phase = workflow_manager.current_phase
            
            # Analysis phase
            job.messages.append("ANALYSIS PHASE: Identifying content themes")
            
            system_message = """You are a content analyst who excels at identifying content opportunities and organizing information.
            
            Your specific responsibilities:
            1. Review the brand brief and search results provided by the ResearchAgent
            2. Identify exactly 6 high-level content themes that would be valuable for the brand
            3. Present these themes in a structured format for user selection
            
            Each theme should:
            - Address a specific audience need or pain point
            - Align with the brand's offering and expertise
            - Have potential for multiple related subtopics
            - Offer strategic value (SEO, thought leadership, etc.)
            
            FORMAT YOUR OUTPUT:
            
            ## Content Themes
            
            1. **[Theme Title]**
               [2-3 sentence description explaining the theme and its value]
            
            2. **[Theme Title]**
               [2-3 sentence description explaining the theme and its value]
            
            [Continue for all 6 themes]
            """
            
            user_message = f"""
            ## Brand Brief
            {brand_brief}
            
            ## Search Results Analysis
            {search_analysis}
            
            Please identify 6 high-level content themes based on this information.
            """
            
            response = run_agent_with_openai(system_message, user_message)
            
            # Parse the themes
            themes = []
            if "## Content Themes" in response:
                themes_text = response.split("## Content Themes", 1)[1].strip()
                
                import re
                pattern = r'(\d+)\.\s+\*\*(.*?)\*\*\s+(.*?)(?=\d+\.\s+\*\*|\Z)'
                matches = re.finditer(pattern, themes_text, re.DOTALL)
                
                for match in matches:
                    theme_num = match.group(1).strip()
                    title = match.group(2).strip()
                    description = match.group(3).strip()
                    
                    themes.append({
                        "number": int(theme_num),
                        "title": title,
                        "description": description
                    })
            
            job.content_themes = themes
            job.progress = 60
            job.messages.append(f"Identified {len(themes)} content themes")
            
            # Advance workflow to THEME_SELECTION phase
            workflow_manager.advance_phase()  # To THEME_SELECTION
            job.workflow_state = workflow_manager.save_state()
            job.current_phase = workflow_manager.current_phase
            
            # Wait for user to select a theme
            job.status = 'awaiting_selection'
            job.messages.append("Waiting for user to select a content theme")
            
        except Exception as e:
            job.status = 'error'
            job.error = f"Error in AI processing: {str(e)}"
            job.messages.append(f"Error: {str(e)}")
            app.logger.error(f"Error in AI processing: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
    
    except Exception as e:
        job.status = 'error'
        job.error = str(e)
        job.messages.append(f"Error: {str(e)}")
        app.logger.error(f"Error processing job {job_id}: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())

def continue_workflow_after_selection(job_id):
    """Continue the workflow after theme selection"""
    job = Job.get_by_id(job_id)
    
    try:
        workflow_manager = WorkflowManager()
        workflow_manager.load_state(job.workflow_state)
        
        # Get the selected theme
        selected_theme = job.selected_theme
        if not selected_theme:
            job.status = 'error'
            job.error = "No theme was selected"
            job.messages.append("Error: No theme was selected")
            return
        
        # Strategy phase
        job.messages.append("STRATEGY PHASE: Creating content cluster framework")
        
        from utils.agents import run_agent_with_openai
        
        system_message = """You are a content strategist who excels at creating strategic topic clusters and content hierarchies.
        
        Your specific responsibilities:
        1. Based on the user-selected theme and brand brief, create a comprehensive content cluster framework
        2. Design a hierarchy with pillar topics and supporting subtopics
        3. Focus on strategic value, search intent, and content flow
        
        FORMAT YOUR OUTPUT:
        
        ## Content Cluster: [Theme Name]
        
        ### Brand Alignment
        [2-3 sentences explaining how this content cluster aligns with the brand]
        
        ### Pillar Topic 1: [Topic Name]
        - **Primary Search Intent**: [Informational/Navigational/Transactional]
        - **Target Audience**: [Specific segment]
        - **Strategic Value**: [SEO/Thought Leadership/Lead Generation/etc.]
        
        #### Supporting Subtopics:
        1. [Subtopic 1]
        2. [Subtopic 2]
        3. [Subtopic 3]
        
        [Repeat for 2-3 more pillar topics]
        """
        
        user_message = f"""
        ## Brand Brief
        {job.brand_brief}
        
        ## Selected Theme
        **{selected_theme['title']}**
        {selected_theme['description']}
        
        Please create a content cluster framework based on this theme.
        """
        
        try:
            content_cluster = run_agent_with_openai(system_message, user_message)
            
            job.content_cluster = content_cluster
            job.progress = 70
            job.messages.append("Completed content cluster framework")
            
            # Advance workflow to CONTENT_IDEATION phase
            workflow_manager.advance_phase()  # To CONTENT_IDEATION
            job.workflow_state = workflow_manager.save_state()
            job.current_phase = workflow_manager.current_phase
            
            # Content ideation phase
            job.messages.append("CONTENT IDEATION PHASE: Developing article ideas")
            
            system_message = """You are a content writer who excels at creating compelling article ideas and titles for blog content.
            
            Your specific responsibilities:
            1. Review the strategist's content cluster framework and the brand brief
            2. Create article concepts for both pillar content and supporting spoke articles
            3. Develop titles that are both SEO-friendly and engaging to readers
            
            For each pillar topic, create:
            - 1 in-depth pillar article concept with title and brief description
            - 3-5 supporting spoke article concepts with titles and brief descriptions
            
            FORMAT YOUR OUTPUT:
            
            ## Content Ideas: [Theme Name]
            
            ### Pillar Article: [Compelling Title]
            - **Target Keyword**: [Primary keyword]
            - **Word Count**: [Recommended length]
            - **Article Type**: [Guide/How-To/List/etc.]
            - **Description**: [2-3 sentence summary of the article content]
            
            ### Supporting Articles:
            
            1. **[Spoke Article Title #1]**
               - **Target Keyword**: [Related keyword]
               - **Description**: [1-2 sentence summary]
            
            2. **[Spoke Article Title #2]**
               - **Target Keyword**: [Related keyword]
               - **Description**: [1-2 sentence summary]
            
            [Continue for all supporting articles]
            
            [Repeat for each pillar topic in the content cluster]
            """
            
            user_message = f"""
            ## Brand Brief
            {job.brand_brief}
            
            ## Selected Theme
            **{selected_theme['title']}**
            {selected_theme['description']}
            
            ## Content Cluster Framework
            {content_cluster}
            
            Please create article ideas based on this content cluster framework.
            """
            
            article_ideas = run_agent_with_openai(system_message, user_message)
            
            job.article_ideas = article_ideas
            job.progress = 85
            job.messages.append("Developed article ideas for the content plan")
            
            # Advance workflow to EDITORIAL phase
            workflow_manager.advance_phase()  # To EDITORIAL
            job.workflow_state = workflow_manager.save_state()
            job.current_phase = workflow_manager.current_phase
            
            # Editorial phase
            job.messages.append("EDITORIAL PHASE: Refining the content plan")
            
            system_message = """You are a content editor who excels at refining content plans for clarity, style, and strategic alignment.
            
            Your specific responsibilities:
            1. Review the entire content plan created by previous agents
            2. Ensure consistency in tone, terminology, and approach across all proposed content
            3. Refine article titles for SEO, brand alignment, and audience appeal
            4. Format the final deliverable in professional Markdown
            5. Add strategic recommendations and implementation notes
            
            FORMAT YOUR OUTPUT:
            
            # Final Content Plan
            
            ## Executive Summary
            [3-5 sentences summarizing the overall content strategy and expected outcomes]
            
            ## Brand Brief
            [Include the refined brand brief]
            
            ## Selected Theme: [Theme Name]
            [Brief description of why this theme is strategically valuable]
            
            ## Content Cluster Structure
            [Include the refined content cluster framework]
            
            ## Article Recommendations
            [Include the refined article concepts, organized by pillar topics]
            
            ## Implementation Guidelines
            - **Recommended Publishing Cadence**: [e.g., 2 articles per week]
            - **Content Distribution Channels**: [Recommendations based on brand and audience]
            - **Success Metrics**: [KPIs to track]
            - **Additional Considerations**: [Any other strategic notes]
            
            ## Next Steps
            [3-5 bullet points outlining recommended next actions]
            """
            
            user_message = f"""
            ## Brand Brief
            {job.brand_brief}
            
            ## Selected Theme
            **{selected_theme['title']}**
            {selected_theme['description']}
            
            ## Content Cluster Framework
            {content_cluster}
            
            ## Article Ideas
            {article_ideas}
            
            Please create the final content plan by reviewing and refining all of the above components.
            """
            
            final_plan = run_agent_with_openai(system_message, user_message)
            
            job.final_plan = final_plan
            job.progress = 100
            
            # Complete the workflow
            workflow_manager.advance_phase()  # To COMPLETION
            job.workflow_state = workflow_manager.save_state()
            job.current_phase = workflow_manager.current_phase
            job.status = 'completed'
            job.completed_at = datetime.now().isoformat()
            job.messages.append("Workflow complete! Content plan is ready.")
            
        except Exception as e:
            job.status = 'error'
            job.error = f"Error in AI processing: {str(e)}"
            job.messages.append(f"Error: {str(e)}")
            app.logger.error(f"Error in AI processing: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
    
    except Exception as e:
        job.status = 'error'
        job.error = str(e)
        job.messages.append(f"Error: {str(e)}")
        app.logger.error(f"Error in theme selection workflow: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())

if __name__ == '__main__':
    app.run(debug=True) 