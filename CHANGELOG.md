# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日はリポジトリ内のバージョン情報（kabusys.__version__ = "0.1.0"）に基づき記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回公開リリース。

### 追加 (Added)
- パッケージ構成を追加
  - kabusys パッケージ（サブパッケージ: data, strategy, execution, monitoring をエクスポート）
- バージョン情報
  - kabusys.__version__ = "0.1.0"

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - .env と .env.local の読み込み優先順位を実装（OS環境変数優先、.env.local は override）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能（テスト用途）
  - .env パーサは export KEY=val、クォート文字列（エスケープ考慮）、インラインコメント処理などに対応
  - Settings クラスを提供（J-Quants、kabu API、Slack、DBパス、環境種別/ログレベル検証などのプロパティを含む）
  - 有効な環境値検証（KABUSYS_ENV、LOG_LEVEL）

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期BS/PL）、JPXマーケットカレンダーを取得する関数を実装
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 認証トークン取得機能: get_id_token（リフレッシュトークンからIDトークンを取得）
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装
  - リトライロジック: 指数バックオフ、最大3回、HTTP 408/429/5xx を対象（429 は Retry-After 優先）
  - 401 時の自動トークンリフレッシュ（1 回のみ）とIDトークンのモジュール内キャッシュ化
  - ページネーション対応（pagination_key を追跡して重複を回避）
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）
  - 値変換ユーティリティ: _to_float / _to_int（失敗時に None を返す、安全な変換ロジック）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存し、記事と銘柄の紐付けを行うフルワークフローを実装
    - fetch_rss: RSS 取得・XML パース・記事整形（title/content の前処理）を実装
    - save_raw_news: INSERT ... RETURNING を用いたチャンク単位のトランザクション挿入（冪等）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（RETURNING で挿入数を取得）
    - extract_stock_codes: テキストから銘柄コード（4桁）を抽出（既知コードセットでフィルタ、重複除去）
    - run_news_collection: 複数ソースからの収集を統合し、個々のソース失敗を隔離して継続処理
  - セキュリティ・堅牢性対策
    - defusedxml による XML パース（XML Bomb 等の緩和）
    - SSRF 対策: URL スキーム検証 (http/https 限定)、リダイレクト先のスキーム/プライベートIP検査、ホストのプライベート判定
    - 最大受信サイズ制限 (MAX_RESPONSE_BYTES = 10MB)、gzip 解凍後サイズも検査（Gzip bomb 対策）
    - トラッキングパラメータ（utm_* など）を除去して URL を正規化、記事ID は正規化URLの SHA-256（先頭32文字）で生成（冪等）
    - HTTP ヘッダに User-Agent と Accept-Encoding 指定、Content-Length の事前チェック
  - テキスト前処理: URL 除去、連続空白の正規化など

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤーに対応したテーブル群を定義する DDL を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに妥当性制約（CHECK や NOT NULL、PRIMARY KEY、外部キー）を設定
  - 頻出クエリを想定したインデックス群を定義
  - init_schema(db_path) により父ディレクトリ自動作成→DuckDB 接続→DDL/INDEX実行（冪等）
  - get_connection(db_path) による既存DBへの接続関数を提供

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラス: ETL 実行結果・品質問題・エラーメッセージを集約
  - 差分更新ヘルパー: テーブルの最終日付取得やトレーディングデイ調整を実装（_get_max_date, _adjust_to_trading_day 等）
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装
  - run_prices_etl: 株価差分ETLのロジックを実装（差分算出、バックフィル日数の考慮、jquants_client を利用した取得と保存）
  - 設計方針の反映: 差分更新、backfill ドメイン、品質チェック（quality モジュールと連携する想定。quality モジュールは外部参照）

### 変更 (Changed)
- 初回リリースのため該当なし（新規追加が中心）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 破壊的変更 (Removed / Breaking Changes)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- XML パースに defusedxml を使用して XXE / XML Bomb の緩和を実装
- RSS フェッチに対する SSRF 対策を多数導入（スキーム検証、リダイレクト検査、プライベートIPチェック）
- .env の読み込みは OS 環境変数をデフォルトで保護し、.env.local の上書きは明示的に許容

---

注:
- 各モジュールはタイプヒント・ログ出力・トランザクション処理を採用しており、テスト容易性と運用時の監査性（fetched_at 等）を重視した設計です。
- pipeline モジュールでは品質チェック（quality モジュール）と統合することを想定していますが、その実装は別モジュール（外部）に依存します。
- run_prices_etl やその他の ETL 関数は、ターゲット日やバックフィル方針に基づき差分取得を行います。必要に応じて id_token を注入してテスト可能です。