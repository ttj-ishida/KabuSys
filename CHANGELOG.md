CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」（https://keepachangelog.com/ja/）に準拠しています。

0.1.0 - 2026-03-18
-----------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
- パッケージ構成の追加:
  - kabusys.config: 環境変数／設定管理機能を提供。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパース実装（コメント行、exportプレフィックス、クォート／エスケープ、インラインコメントの処理などに対応）。
    - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス / システム環境（env, log_level, is_live 等）をプロパティで取得、入力値検証を実施。
  - kabusys.data.jquants_client: J-Quants API クライアント。
    - 株価日足、財務データ、マーケットカレンダーの取得 API（ページネーション対応）。
    - 固定間隔スロットリングによるレート制限（デフォルト 120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）と HTTP ステータスに基づくリトライロジック。
    - 401 発生時の自動トークンリフレッシュ（1 回まで）とトークンキャッシュ機構。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE を利用）。
    - 型変換ユーティリティ（_to_float, _to_int）。
  - kabusys.data.news_collector: RSS ニュース収集モジュール。
    - RSS フィード取得、XML パース（defusedxml による安全対策）、テキスト前処理（URL 除去・空白正規化）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
    - SSRF 対策（スキーム検証、リダイレクト先の事前検証、プライベート IP 判定）、受信サイズ上限（10MB）チェック、gzip 解凍後の追加チェック。
    - DuckDB への冪等保存（save_raw_news でチャンク INSERT + RETURNING を利用）と記事―銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）。
    - 銘柄コード抽出ユーティリティ（4桁数字の抽出と既知コードフィルタリング）。
    - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソース単位での独立エラーハンドリング、既知銘柄紐付け）。
  - kabusys.data.schema: DuckDB スキーマ定義・初期化。
    - Raw / Processed / Feature / Execution 層を想定したテーブル群を定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - 各種制約（PK, CHECK, FOREIGN KEY）と索引を定義。
    - init_schema(db_path) によりディレクトリ自動作成と DDL 実行による初期化を実現。get_connection で既存 DB へ接続可能。
  - kabusys.data.pipeline: ETL パイプラインの基礎実装。
    - ETLResult データクラス（取得数、保存数、品質問題、エラー記録等）。
    - 差分更新ヘルパー（最終取得日の取得、取引日補正）。
    - run_prices_etl（差分取得ロジック、バックフィル日数対応、jquants_client を用いた取得・保存の呼び出し）を実装（差分更新の枠組み）。
  - パッケージ初期化: src/kabusys/__init__.py にパッケージ名・__version__・__all__ を追加。
  - 空モジュールの追加: execution と strategy のパッケージスケルトンを用意（今後の拡張ポイント）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- RSS XML パースに defusedxml を採用し XML Bomb などの攻撃を軽減。
- fetch_rss / _urlopen レイヤで SSRF 対策を実装（スキーム検証、プライベートホスト検査、リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する仕組み（.env と .env.local の読み込み順、既存環境変数の上書き制御）。

Notes / Known limitations
- pipeline.run_prices_etl の戻り値・処理は ETLResult と組み合わせて利用する想定だが、実装は差分取得と保存呼び出しの主要な部分を実装した段階。今後の品質チェック（quality モジュール）や他種 ETL ジョブ（財務・カレンダー等）の統合を予定。
- strategy、execution モジュールはスケルトン状態のため、戦略ロジック・発注ロジックは未実装。
- テスト用フック: news_collector._urlopen などをモックしてテスト可能な設計だが、実際のユニットテストは別途追加予定。

Unreleased
- 今後の予定:
  - pipeline の完全な ETL ワークフロー（品質チェック統合、結果の監査ログ出力）。
  - strategy / execution の実装（シグナル生成、注文発行、kabuステーション連携）。
  - 単体テスト・CI の整備とドキュメント充実。
  - error / observability 周りの改善（メトリクス、詳細ログ）。

（注）上記はソースコードから推測してまとめた変更履歴です。実際のリリースノート作成時には追加の運用情報や既知の不具合情報を追記してください。