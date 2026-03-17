# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更点は後方互換性や設計意図が分かるように記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム KabuSys のコア機能群を実装しました。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加 (src/kabusys/__init__.py)。
  - サブパッケージの骨組みを追加 (data, strategy, execution, monitoring)。

- 設定管理
  - .env ファイルおよび環境変数から設定を読み込む設定モジュールを実装 (src/kabusys/config.py)。
    - .git または pyproject.toml を探索してプロジェクトルートを自動特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export 付き行、クォート処理、インラインコメント処理などを考慮した .env パーサーを実装。
    - 必須環境変数取得時に未設定なら ValueError を報告する _require を提供。
    - 環境 (development, paper_trading, live) とログレベルのバリデーションを実装。
    - DB パス等を Path 型で提供するプロパティを用意。

- J-Quants API クライアント
  - J-Quants から株価日足、財務情報、マーケットカレンダーを取得するクライアントを実装 (src/kabusys/data/jquants_client.py)。
    - API レート制限 (120 req/min) を守る固定間隔スロットリングの RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
    - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回再試行する機能を実装（無限再帰を防止）。
    - id_token のモジュールレベルキャッシュを実装し、ページネーション間で共有。
    - ページネーション対応の fetch_* 関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - データ保存関数を実装（冪等性を確保: ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。
    - 取得時刻 (fetched_at) を UTC で記録して Look-ahead Bias のトレースを可能に。

- ニュース収集（RSS）
  - RSS からニュースを収集して DuckDB に保存するモジュールを実装 (src/kabusys/data/news_collector.py)。
    - RSS フィード取得 (fetch_rss)、前処理 (URL 除去、空白正規化)、記事ID生成、DB 保存を実装。
    - 記事ID は URL 正規化後の SHA-256 の先頭32文字で生成し冪等性を確保（utm_* 等のトラッキングパラメータを除去）。
    - defusedxml を使った XML パースで XML Bomb 等の攻撃を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先のスキーム・ホスト検証を行うカスタム HTTPRedirectHandler を実装。
      - リダイレクト先のホストがプライベート/ループバック/リンクローカルでないことをチェック。
      - DNS 解決失敗は安全側に扱う（保守性を考慮）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズ検査を実装してメモリ DoS を防止。
    - Gzip レスポンスの処理、Content-Length の事前チェック、XML パース失敗時のフォールバックを実装。
    - DuckDB への挿入はトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入されたレコードを正確に取得する: save_raw_news, save_news_symbols, _save_news_symbols_bulk。
    - 銘柄コード抽出機能を提供（4桁数字、known_codes によるフィルタリング）: extract_stock_codes。
    - デフォルト RSS ソースとして Yahoo ビジネス RSS を追加。

- DuckDB スキーマ
  - DataSchema.md に基づいた DuckDB スキーマを実装 (src/kabusys/data/schema.py)。
    - Raw / Processed / Feature / Execution レイヤーのテーブルを定義。
    - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
    - features, ai_scores の Feature レイヤー。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
    - 頻出クエリに対応するインデックスを複数定義。
    - init_schema(db_path) による初期化を実装（ディレクトリ自動作成、冪等的 DDL 実行）。get_connection を提供。

- ETL パイプライン
  - ETL 管理モジュールを実装 (src/kabusys/data/pipeline.py)。
    - 差分更新、バックフィル（デフォルト backfill_days=3）、市場カレンダーの先読み（lookahead）、品質チェックへのフックを想定する設計。
    - ETLResult データクラスを実装し、処理結果、品質問題、エラー一覧を集約可能に。
    - 各種ヘルパー: テーブル存在確認、最大日付取得、営業日調整を実装。
    - 差分更新を行う run_prices_etl を実装（date_from 自動算出、J-Quants から差分取得、保存）。品質チェックモジュール quality との連携を想定（品質問題は収集して ETL を継続する設計）。
    - 最小データ開始日を定義（2017-01-01）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- RSS パーサーで defusedxml を利用し XML 攻撃を軽減。
- RSS フェッチで SSRF 対策を実施（スキーム検証、プライベート IP 検出、リダイレクト検査）。
- .env 読み込みで OS 環境変数の上書き制御（protected set）を導入。

### 注意事項 / 設計上の決定
- J-Quants API のレート制限を固定間隔スロットリングで実装（単純で確実な制御を優先）。
- id_token の自動リフレッシュは 401 時に 1 回のみ行い、無限ループを回避する設計。
- DuckDB への保存は可能な限り冪等にして再実行可能に（ON CONFLICT DO UPDATE / DO NOTHING を多用）。
- ニュース記事 ID は URL 正規化 + ハッシュで生成し冪等性を担保。トラッキングパラメータは除去。
- ETL は Fail-Fast とせず、品質チェックでの問題を収集しつつ処理を継続する方針（呼び出し元での判断を想定）。

今後の予定（例）
- strategy / execution / monitoring の具体実装（現状はパッケージ骨組みのみ）。
- quality モジュールの完全実装および ETL での自動アラート連携。
- J-Quants クライアントのさらなるテスト・メトリクス追加。
- Slack 等通知機能・実運用向け監視の実装。

---
（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして用いる場合は実行環境やパッケージ情報に合わせて日付・項目を調整してください。