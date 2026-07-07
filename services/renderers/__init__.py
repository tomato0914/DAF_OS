"""
DAF OS Quest98 — Renderers package

画像生成エンジンごとの実装（Pillow / 将来のOpenAI・Google・FLUX・
Stability AI等）を置くディレクトリ。各Rendererモジュールは共通の
インターフェース（render_stamp(phrase, index) / render_icon(size)）を
公開し、services/image_generation_service.py から選択・呼び出される。
Asset Generator（services/asset_generator_service.py）はどのRendererが
使われているかを知らない。
"""
