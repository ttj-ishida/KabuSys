# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に従います。
Semantic Versioning に従います。

## [0.1.0] - 2026-03-18

初回リリース。日本株の自動売買プラットフォーム「KabuSys」の基盤機能を実装しました。主に以下のサブパッケージ・機能を追加しています。

### 追加 (Added)
- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージ公開 API (`__all__`) に data, strategy, execution, monitoring を追加（strategy と execution は初期プレースホルダとして存在）。

- 環境設定・読み込み (`kabusys.config`)
  - Settings クラスを追加し、アプリケーション設定を環境変数から取得する仕組みを実装。
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート判定は `.git` または `pyproject.toml` を探索）。
  - 優先度: OS 環境変数 > .env.local > .env（`.env.local` は override=True）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能（テスト支援）。
  - .env パーサを実装し、export プレフィックス、クォート文字列、インラインコメント、エスケープ文字に対応。
  - 必須 env の取得時に検証を行う `_require()` を追加（未設定時は ValueError）。
  - 各種設定プロパティを実装:
    - J-Quants / kabuステーション / Slack 用トークン・URL
    - データベースパス（DuckDB / SQLite）
    - 環境種別（development, paper_trading, live）とログレベルの検証
    - is_live / is_paper / is_dev のブールプロパティ

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しラッパー `_request()` を実装（JSON デコード・例外処理含む）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 _RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）、ステータス 408/429/5xx を再試行対象に設定。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライする仕組みを実装（無限再帰対策あり）。
  - ページネーション対応（pagination_key を利用）で fetch_* 系関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存用関数を実装（冪等性を担保する ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データ型変換ユーティリティ `_to_float`, `_to_int` を追加（不正値や小数切捨ての扱いを明確化）。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead bias のトレースが可能。

- RSS ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集機能を実装（defusedxml を使った安全な XML パース）。
  - セキュリティ・堅牢性対策を多数実装:
    - SSRF 対策（リダイレクト先のスキーム検証・ホストのプライベートアドレス判定）
    - リクエストサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip-bomb 対策）
    - URL スキーム検証（http/https のみ許可）
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証（utm_* 等のトラッキングパラメータを除去して正規化）。
  - テキスト前処理関数 preprocess_text（URL 除去、空白正規化）を実装。
  - fetch_rss 関数: RSS の取得・パース・記事抽出、content:encoded の優先処理、pubDate のパース（RFC2822 対応）を実装。
  - DuckDB への保存関数:
    - save_raw_news: INSERT ... RETURNING を使い新規挿入された記事 ID を返す（チャンク・トランザクション処理）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING、RETURNING で正確な挿入数を返す）。
  - 銘柄コード抽出ロジック extract_stock_codes（4桁数字を検出し known_codes に含まれるもののみ返す）を実装。
  - run_news_collection: 複数ソースを順次処理し、失敗したソースはスキップしつつ他ソースは継続する堅牢な統合収集ジョブを実装。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution）。
  - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
  - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature テーブル: features, ai_scores
  - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を付与。
  - インデックスを定義して頻出クエリに備える（code/date、status、order_id 等）。
  - init_schema(db_path) を提供し、ファイルパスの親ディレクトリ自動作成、DDL を順序考慮して冪等的に実行。
  - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETLResult データクラスを実装し、ETL の結果・品質問題・エラーログを集約。
  - 差分更新を行う各種ヘルパーを実装:
    - テーブル存在確認、最大日付取得、取引日調整ロジック（market_calendar に基づく過去方向調整）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl（株価差分 ETL）の基盤を実装（差分算出、backfill_days による再取得、J-Quants からの取得と保存呼び出し）。
  - 設計方針に基づき、背後の quality モジュールとの連携点（品質検査結果の集約）を用意。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を採用し XML 関連の攻撃を緩和。
- RSS フェッチで SSRF を防ぐ検証を導入（スキーム検査、プライベートアドレス拒否、リダイレクト時の検査）。
- ネットワーク受信データのサイズ制限（最大 10MB）と gzip 解凍後のサイズ検査を実装。

### 既知の制限 / 注意点 (Known issues / Notes)
- strategy と execution サブパッケージは初期時点ではモジュールのプレースホルダのみ（実際の戦略ロジックや発注ロジックは未実装）。
- quality モジュールの実装は外部（別ファイル）に依存しており、ETL の品質チェック統合は quality の実装状況に依存する。
- jquants_client は urllib を用いた実装のため、より高度な HTTP 要求管理（接続プーリング・セッション管理）が必要な場合は将来的に httpx / requests 等の導入を検討。

---

（本 CHANGELOG はソースコードの内容から推定して作成しています。実際のリリースノートや運用上の扱いはプロジェクト方針に従って調整してください。）