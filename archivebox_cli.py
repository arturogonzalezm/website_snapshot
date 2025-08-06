import os
import sys
import subprocess
import datetime
import click

# === Default Configuration ===
DEFAULT_ARCHIVEBOX_DIR = os.path.join(os.getcwd(), 'srv', 'archivebox')  # Default data directory

@click.group()
@click.option('--data-dir', 'archivebox_dir', default=DEFAULT_ARCHIVEBOX_DIR,
              help='Path to ArchiveBox data directory')
@click.option('--binary', 'archivebox_bin', default=None,
              help='Path to ArchiveBox CLI binary (default: auto-detect)')
@click.pass_context
def cli(ctx, archivebox_dir, archivebox_bin):
    """ArchiveBox Automation CLI"""
    archivebox_dir = os.path.abspath(archivebox_dir)
    ctx.ensure_object(dict)
    ctx.obj['ARCHIVEBOX_DIR'] = archivebox_dir
    ctx.obj['ARCHIVEBOX_BIN'] = archivebox_bin
    ctx.obj['URLS_FILE'] = os.path.join(archivebox_dir, 'urls.txt')


def _run(ctx, *args, stdin=None):
    """Internal: Run ArchiveBox command or fallback to python module"""
    base_bin = ctx.obj['ARCHIVEBOX_BIN']
    if base_bin:
        cmd = [os.path.abspath(base_bin)] + list(args)
    else:
        cmd = ['archivebox'] + list(args)
    try:
        return subprocess.run(cmd, cwd=ctx.obj['ARCHIVEBOX_DIR'], check=True, stdin=stdin)
    except (FileNotFoundError, subprocess.CalledProcessError):
        fallback = [sys.executable, '-m', 'archivebox'] + list(args)
        click.echo(f"Falling back to: {' '.join(fallback)}")
        return subprocess.run(fallback, cwd=ctx.obj['ARCHIVEBOX_DIR'], check=True, stdin=stdin)

@cli.command()
@click.pass_context
def init(ctx):
    """Initialize ArchiveBox environment (force if directory not empty)"""
    d = ctx.obj['ARCHIVEBOX_DIR']
    os.makedirs(d, exist_ok=True)
    _run(ctx, 'init', '--force')
    click.echo(f"Initialized ArchiveBox in {d}.")

@cli.command()
@click.argument('url')
@click.option('--index-only/--no-index-only', 'index_only', default=True,
              help='Only add to index without running extractors')
@click.pass_context
def add(ctx, url, index_only):
    """Add a single URL to ArchiveBox for archiving"""
    args = ['add', url]
    if index_only:
        args.insert(1, '--index-only')
    _run(ctx, *args)
    click.echo(f"Added URL: {url}")

@cli.command()
@click.option('--index-only/--no-index-only', 'index_only', default=True,
              help='Only add to index without running extractors')
@click.pass_context
def bulk(ctx, index_only):
    """Add all URLs from urls.txt to ArchiveBox via stdin"""
    d = ctx.obj['ARCHIVEBOX_DIR']
    urls_file = ctx.obj['URLS_FILE']
    if not os.path.isfile(urls_file):
        click.echo(f"URLs file not found: {urls_file}")
        return
    args = ['add']
    if index_only:
        args.append('--index-only')
    # Pipe URLs through stdin
    with open(urls_file, 'rb') as f:
        _run(ctx, *args, stdin=f)
    click.echo(f"Archived all URLs from {urls_file}.")

@cli.command(name='list')
@click.pass_context
def _list(ctx):
    """List all archived snapshots with dates"""
    _run(ctx, 'manage', 'list')

@cli.command()
@click.pass_context
def schedule(ctx):
    """Run a scheduled snapshot for all URLs (to be triggered via cron)"""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    click.echo(f"[{now}] Starting scheduled archive run...")
    ctx.invoke(bulk)
    click.echo("Scheduled archive run complete.")

if __name__ == '__main__':
    cli()
