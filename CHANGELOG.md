CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)。
- 基本パッケージ構成を追加:
  - src/kabusys/__init__.py: パッケージ名とバージョン定義、公開モジュール一覧。
  - 空のサブパッケージプレースホルダ: strategy, execution。
- 環境変数・設定管理:
  - src/kabusys/config.py を追加。
  - .env / .env.local の自動読み込み機構（プロジェクトルートは .git または pyproject.toml で検出）。
  - 読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
  - .env パーサー実装（export プレフィックス、クォート、インラインコメントの扱い）を提供。
  - Settings クラスを公開し、J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境種別（development/paper_trading/live）やログレベルの検証ロジックを実装。
- J-Quants API クライアント:
  - src/kabusys/data/jquants_client.py を追加。
  - API 呼び出しの共通処理を実装（JSON パース、タイムアウト、ヘッダ設定）。
  - レート制限（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス (408, 429, 5xx)。
  - 401 発生時はリフレッシュトークンで id_token を自動更新して 1 回再試行する仕組み。
  - ページネーション対応のデータ取得関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - fetched_at（UTC）を記録して Look-ahead バイアスの追跡を可能に。
  - 型変換ユーティリティ (_to_float, _to_int) を実装。
- ニュース収集モジュール:
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィード取得・パース・前処理・DB 保存の一連処理を実装。
  - デフォルトソース（Yahoo Finance のカテゴリ RSS）を定義。
  - セキュリティ・耐障害性を考慮した設計:
    - defusedxml による XML パース（XML Bomb 対策）。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検査、プライベートIP/ループバックの拒否。
    - リダイレクト時に事前検証するカスタムハンドラ実装。
  - URL 正規化とトラッキングパラメータ削除（utm_ 等）、正規化 URL の SHA-256（先頭32文字）から記事 ID を生成して冪等性を担保。
  - テキスト前処理（URL除去、空白正規化）。
  - DuckDB へのバルク挿入をチャンク化してトランザクションで実行し、INSERT ... RETURNING を用いて実際に挿入された件数を返す実装:
    - save_raw_news, save_news_symbols, _save_news_symbols_bulk
  - 銘柄コード抽出ユーティリティ（4桁数字）と、既知銘柄セットを用いたフィルタリング。
  - run_news_collection: 複数 RSS ソースを独立して処理し、失敗したソースも他のソースに影響を与えない設計。新規記事に対する銘柄紐付け処理を一括で実行。
- DuckDB スキーマ定義と初期化:
  - src/kabusys/data/schema.py を追加。
  - Raw / Processed / Feature / Execution レイヤーに対応するテーブル DDL を網羅的に定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義と外部キー依存を考慮した作成順を実装。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行・接続返却、get_connection() を提供。
- ETL パイプライン:
  - src/kabusys/data/pipeline.py を追加。
  - ETLResult データクラスを導入（取得数、保存数、品質問題、エラーの集約）。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得）を実装。
  - 市場カレンダーを考慮した営業日調整ロジックを実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl を実装（差分取得、backfill 日数設定、J-Quants クライアント経由で取得・保存）。設計として品質チェック（quality モジュール）との連携を想定。

Security
- news_collector と HTTP 周りで SSRF、XML Attack、巨大レスポンス（メモリ DoS）などに対する複数の防御策を導入。
- config の .env 読み込みは保護された OS 環境変数を上書きしない設計（override/protected パラメータ）。

Notes
- 多くの機能は DuckDB を前提としており、init_schema() による初期化が推奨されます。
- quality モジュールへの依存は pipeline 側で想定されている（品質チェックの統合ポイント）。
- strategy / execution サブパッケージはプレースホルダが存在します。今後の戦略ロジックや発注実装追加を想定。

Acknowledgements
- 初回リリース。今後の拡張でエンドツーエンドの自動売買フロー（シグナル生成→発注→実行監視）を追加予定。