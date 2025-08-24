import os
import json
import datetime
from source import configuration


class PreviewHandler:
    """
    Handles preview and dry-run functionality for the newsletter
    """
    
    def __init__(self):
        self.config = configuration.conf.preview
        self._ensure_output_directory()
    
    def _ensure_output_directory(self):
        """Create output directory if it doesn't exist"""
        if self.config.enabled:
            os.makedirs(self.config.output_directory, exist_ok=True)
    
    def _generate_filename(self, suffix=""):
        """Generate filename with date/timestamp placeholders"""
        filename = self.config.output_filename
        now = datetime.datetime.now()
        
        # Replace placeholders
        filename = filename.replace("{date}", now.strftime("%Y-%m-%d"))
        filename = filename.replace("{time}", now.strftime("%H%M%S"))
        filename = filename.replace("{timestamp}", now.strftime("%Y%m%d_%H%M%S"))
        
        if suffix:
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{suffix}{ext}"
            
        return os.path.join(self.config.output_directory, filename)
    
    def _add_metadata_to_html(self, html_content, metadata):
        """Add metadata to HTML as comments"""
        if not self.config.include_metadata:
            return html_content
            
        metadata_comment = f"""<!--
=== JELLYFIN NEWSLETTER METADATA ===
Generated: {metadata['generation_timestamp']}
Mode: {metadata['mode']}
Movies Found: {metadata['stats']['movies_count']}
TV Episodes Found: {metadata['stats']['tv_episodes_count']}
Template Language: {metadata['template_language']}
SMTP Tested: {metadata.get('smtp_tested', 'N/A')}
=== END METADATA ===
-->
"""
        
        # Insert after DOCTYPE or at the beginning
        if '<!DOCTYPE' in html_content:
            parts = html_content.split('>', 1)
            if len(parts) == 2:
                return parts[0] + '>\n' + metadata_comment + '\n' + parts[1]
        
        return metadata_comment + '\n' + html_content
    
    def save_preview(self, html_content, metadata, mode="preview"):
        """
        Save HTML preview and optional JSON metadata
        
        Args:
            html_content (str): The generated HTML email content
            metadata (dict): Email generation metadata
            mode (str): "preview" or "dry-run"
            
        Returns:
            tuple: (html_file_path, json_file_path or None)
        """
        if not self.config.enabled:
            return None, None
            
        # Generate filenames
        html_file = self._generate_filename()
        
        # Add metadata to HTML
        if self.config.include_metadata:
            html_content = self._add_metadata_to_html(html_content, metadata)
        
        # Save HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Save JSON metadata if enabled
        json_file = None
        if self.config.save_email_data:
            json_file = self._generate_filename("data").replace('.html', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        return html_file, json_file
    
    def get_metadata(self, movies, series, total_tv, total_movie, mode="preview", smtp_tested=False):
        """
        Generate metadata for the email
        
        Args:
            movies (dict): Movies data
            series (dict): Series data
            total_tv (int): Total TV episodes count
            total_movie (int): Total movie count
            mode (str): "preview" or "dry-run"
            smtp_tested (bool): Whether SMTP connection was tested
            
        Returns:
            dict: Email metadata
        """
        now = datetime.datetime.now()
        
        # Prepare movies data for JSON
        movies_list = []
        for movie_id, movie_data in movies.items():
            movies_list.append({
                "name": movie_data.get('name', 'Unknown'),
                "added_date": movie_data.get('created_on', '').split('T')[0],
                "tmdb_id": movie_data.get('tmdb_id', '')
            })
        
        # Prepare series data for JSON
        series_list = []
        for serie_id, serie_data in series.items():
            series_list.append({
                "series_name": serie_data.get('series_name', 'Unknown'),
                "seasons": serie_data.get('seasons', []),
                "episodes": serie_data.get('episodes', []),
                "added_date": serie_data.get('created_on', '').split('T')[0]
            })
        
        return {
            "generation_timestamp": now.isoformat(),
            "mode": mode,
            "smtp_tested": smtp_tested,
            "jellyfin_server": configuration.conf.email_template.jellyfin_url,
            "stats": {
                "movies_count": total_movie,
                "tv_episodes_count": total_tv,
                "total_email_size_kb": 0  # Will be calculated after HTML generation
            },
            "movies": movies_list,
            "tv_shows": series_list,
            "recipients": configuration.conf.recipients if mode == "dry-run" else ["preview-mode"],
            "template_language": configuration.conf.email_template.language,
            "configuration_hash": str(hash(str(configuration.conf.__dict__)))
        }
