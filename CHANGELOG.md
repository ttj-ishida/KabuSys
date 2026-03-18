# Keep a Changelog

すべての変更は逆順（最新が上）で記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システムのコア基盤を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサ実装（シングル/ダブルクォート、export KEY=val 形式、インラインコメント処理対応）。
  - ロード時の既存 OS 環境変数保護（protected set）と .env.local による上書きサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラス実装（J-Quants, kabuステーション, Slack, DB パス, 環境モード・ログレベル検証などのプロパティを提供）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須環境変数取得時のエラーメッセージ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース実装: id token 取得、認証付きリクエスト送信ユーティリティ。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回リトライ（408/429/5xx 対象）、429 の Retry-After サポート。
  - 401 時の自動トークンリフレッシュ（1 回のみ）でリトライする仕組み。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等設計）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を利用して重複や更新に対応
  - データ変換ユーティリティ: _to_float / _to_int（堅牢な型変換ルール）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS 取得・パース・前処理・DB 保存のワークフローを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の緩和）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検査用ハンドラ、初回ホストプライベート判定。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）とgzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ削除（utm_* 等）を実装、記事ID を正規化URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）と RSS pubDate の堅牢なパース。
  - DB 保存処理:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いたチャンク挿入（トランザクションでまとめる）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存（RETURNING を使用して実際に挿入された件数を返す）
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字パターンに基づき known_codes フィルタで絞り込み）。
  - 統合収集ジョブ run_news_collection（複数 RSS ソースの個別ハンドリング、既存記事はスキップ、銘柄紐付けの一括保存）。

- データベーススキーマ & 初期化 (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル：
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK）や外部キーを設定。
  - 頻出クエリ用インデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成 → DDL 実行 → 接続を返す機能を提供。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - 差分更新 / バックフィル（backfill_days デフォルト 3 日）を想定した ETL 設計。
  - 市場カレンダー先読み日数定義（_CALENDAR_LOOKAHEAD_DAYS = 90）。
  - ETLResult dataclass による結果集約（品質問題リスト、エラーリストを含む）。品質チェック結果のシリアライズ(to_dict)を提供。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパー(_adjust_to_trading_day)を実装。
  - 個別 ETL ジョブ用のヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl の骨子を実装（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes）
  - 品質チェックモジュール (quality) 参照（詳細は外部モジュール想定）。品質問題は収集を続行し呼び出し元で判断する設計。

- その他
  - strategy/ と execution/ パッケージのプレースホルダを追加（__init__.py 空実装）。将来的な戦略・発注ロジックの置き場を確保。

### 変更 (Changed)
- 初版のため、既存からの変更はありません。

### 修正 (Fixed)
- 初版のため、修正はありません。

### セキュリティ (Security)
- RSS パーサに defusedxml を利用、SSRF 対策（ホストのプライベート判定、リダイレクト先検査）、レスポンスサイズ制限、URL スキーム検査など複数の安全対策を導入。

### 既知の制限 (Known issues / Notes)
- pipeline.run_prices_etl は基本フローを実装済みだが、pipeline 内で参照する品質チェック（quality モジュール）や一部の管理ロジックは外部/未実装部分に依存します。
- NewsCollector の既定 RSS ソースは Yahoo Finance のビジネスカテゴリのみを登録（DEFAULT_RSS_SOURCES）。実運用ではソース拡充が必要。
- execution / strategy / monitoring の具体的な実装（発注ロジック・モニタリング）は未実装のため、運用用途では追加開発が必要。

### 互換性 (Compatibility)
- 初回リリースのため破壊的変更はなし。

---

作業やリリースノートの追記・修正が必要であれば、どのモジュールに関する追記を希望するか教えてください。具体的な変更点（追加したいリリース日、著者、リリースノートの詳細など）も指定できます。