# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。SemVer に従ってバージョンを管理します。

※ 日付は本コードベースを元に推測して付与しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env の行パーサ実装: コメント、export 形式、シングル/ダブルクォート、エスケープ等に対応。
  - 上書き制御 (override) と保護キー（protected）により OS 環境変数の上書きを防止。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティ（必要時は例外を送出）。
    - 環境（KABUSYS_ENV）のバリデーション（development / paper_trading / live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）とユーティリティ判定プロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API ベース実装（_BASE_URL = https://api.jquants.com/v1）。
  - レート制御: 固定間隔スロットリングで120 req/min を順守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象にリトライ。
  - トークンキャッシュと自動リフレッシュ:
    - id_token のモジュールキャッシュを保持し、401 受信時に一度だけリフレッシュしてリトライ。
    - get_id_token()（refresh token から id_token を取得）を実装。
  - HTTP ユーティリティ: JSON デコードエラーやタイムアウトへの対処。
  - データ取得関数を追加:
    - fetch_daily_quotes (日足 OHLCV、ページネーション対応)
    - fetch_financial_statements (財務四半期データ、ページネーション対応)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への保存関数（冪等）を追加:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ INSERT ... ON CONFLICT DO UPDATE
  - データ変換ユーティリティ: 安全な数値変換 (_to_float / _to_int)、欠損PKのスキップとログ出力。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集基盤を実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時にスキーム検証とホスト/IP のプライベート判定を実施。初回 URL も事前検証。
    - HTTP レスポンスの最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - 許可される URL スキームを http/https のみに制限。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ (utm_*, fbclid, gclid など) を除去してクエリをソート、フラグメント除去等の正規化を実施。
    - 記事ID は正規化後 URL の SHA-256 ハッシュの先頭32文字を採用（冪等性確保）。
  - テキスト前処理: URL 除去、空白正規化。
  - RSS 取得: fetch_rss() が記事リスト（NewsArticle 型）を返却。XML パースエラーやサイズ超過は警告ログで扱い空リストを返す。
  - DuckDB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入IDのリストを返す（チャンク・1トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの (news_id, code) 紐付けをチャンクで保存し、挿入数を正確に返す。
  - 銘柄コード抽出: 正規表現で4桁数字を抽出し known_codes に含まれるものだけ返す。
  - 統合ジョブ run_news_collection: 複数 RSS ソースを独立して処理し、取得失敗はソース単位でスキップ。新規記事に対して銘柄紐付け処理を実行。

- スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DuckDB 用 DDL を包括的に実装（Raw / Processed / Feature / Execution レイヤー）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - パフォーマンス向けインデックスを作成（例: idx_prices_daily_code_date など）。
  - init_schema(db_path) による冪等的なスキーマ初期化と接続返却を提供（親ディレクトリ自動作成を含む）。
  - get_connection(db_path) による既存 DB への接続を提供（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass により ETL 実行結果の構造化（取得数・保存数・品質問題・エラー等）。
  - 差分更新ユーティリティ:
    - テーブル存在チェック、最大日付取得（_get_max_date）、最終取得日の補助関数（get_last_price_date 等）。
    - 市場カレンダーを参照して非営業日を最近の営業日に調整するヘルパー (_adjust_to_trading_day)。
  - run_prices_etl(): 株価日足の差分 ETL 実装（差分算出、backfill_days による再取得制御、jquants_client 経由の取得と保存）。
  - ETL 設計方針の反映: 差分更新、backfill による後出し修正吸収、品質チェックとの連携を想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS 周りのセキュリティ強化（SSRF、XML インジェクション、Gzip bomb、受信サイズ制限）。
- .env 読み込みで OS 環境変数の意図しない上書きを防ぐ保護キー機構。

### Notes / Implementation details
- DuckDB をデータ層として採用しており、各保存関数は冪等性（ON CONFLICT）を念頭に実装されています。
- jquants_client のレートリミッタはモジュール内単一インスタンスで制御する設計です。ページネーション時にトークンを共有するための id_token キャッシュを保持します。
- news_collector は外部ネットワークアクセスを行うため、テスト時は内部関数（例: _urlopen）をモックして差し替えることを想定しています。
- pipeline モジュールは品質チェックモジュール（kabusys.data.quality）と連携する前提で実装されており、重大な品質問題は ETL の継続中にも収集され呼び出し元で判断する設計です。

---

開発・運用に関する不明点や CHANGELOG の追加項目（例えばリリース日や未反映の変更）について指示いただければ、追記・修正します。