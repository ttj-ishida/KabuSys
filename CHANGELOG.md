# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠し、セマンティック バージョニングを使用します。  

リンク: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。以下の主要機能（モジュール）と設計上の配慮を含みます。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョンを設定（__version__ = "0.1.0"）。公開モジュールとして data, strategy, execution, monitoring を列挙。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルや環境変数から設定をロードする Settings クラスを追加。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml を探索）を起点に .env/.env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサの実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどを正しく解釈。
  - 必須環境変数取得時に _require による検査。環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - データベースファイルパス（duckdb/sqlite）のデフォルトと Path 型への変換ユーティリティ。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API ベース URL 定数、認証（リフレッシュトークンから id_token 取得）を実装。
  - レート制限管理 (_RateLimiter): 固定間隔（120 req/min）でスロットリング。
  - 再試行ロジック: 指数バックオフを用いた最大 3 回のリトライ（408/429/5xx 対応）。429 では Retry-After ヘッダを優先。
  - 401 応答時の id_token 自動リフレッシュ（1 回のみ）と安全な無限再帰防止。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応、pagination_key の扱い）。
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - データ整形ユーティリティ: _to_float, _to_int（堅牢な変換ロジック）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集パイプラインを実装（DEFAULT_RSS_SOURCES を含む）。
  - セキュリティ強化:
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - URL スキーム検証（http/https のみ許可）とリダイレクト時の事前検証用ハンドラ（_SSRFBlockRedirectHandler）による SSRF 対策。
    - ホストがプライベート・ループバック等の場合はアクセス拒否（_is_private_host）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _TRACKING_PARAM_PREFIXES）。
  - 記事 ID 生成: 正規化 URL の SHA-256 先頭32文字で冪等性を担保（_make_article_id）。
  - テキスト前処理（URL 除去・空白正規化）。
  - RSS 取得処理: fetch_rss（名前空間や description/content:encoded を考慮）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いたトランザクションバルク保存、チャンク処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付け保存（ON CONFLICT DO NOTHING + RETURNING で挿入数を正確に取得）。
  - 銘柄コード抽出ロジック: 4桁数字の抽出と known_codes によるフィルタ（extract_stock_codes）。
  - 統合収集ジョブ: run_news_collection（複数ソースの独立したエラーハンドリング、新規挿入に対する銘柄紐付けの一括処理）。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用の包括的スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 各種テーブル DDL: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - インデックス定義（頻出クエリを想定したインデックス群）。
  - init_schema(db_path): ディレクトリ作成を含めたスキーマ初期化（冪等）。
  - get_connection(db_path): 既存 DB への接続取得。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による ETL 実行結果の構造化（品質問題、エラーの集約）。
  - 差分更新ヘルパー: テーブル存在チェック、最大日付取得ユーティリティ。
  - 市場カレンダーに基づく営業日調整ロジック（_adjust_to_trading_day）。
  - 差分更新ロジックの土台（get_last_price_date など）。
  - 個別 ETL ジョブの骨組み: run_prices_etl（差分取得、バックフィル日数設定、最小データ日付考慮、jq.fetch_daily_quotes と jq.save_daily_quotes の組合せ）。※ run_prices_etl の末尾は ETL 処理の続きを想定した実装余地あり。

- その他
  - ディレクトリ構造で strategy と execution のパッケージスケルトンを追加（将来的な戦略／発注実装用）。
  - 各モジュールでロギングを活用（logger を通じた情報・警告ログ出力）。
  - テスト容易性の配慮:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロード抑制。
    - jquants_client の id_token 注入可能設計（テストでのモック化容易）。
    - news_collector._urlopen をモック差替え可能に設計。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Security
- RSS/XML 処理におけるセキュリティ考慮:
  - defusedxml の採用、SSRF 検査、リダイレクト検証、レスポンスサイズ制限、gzip 解凍時のサイズチェックにより外部データ取り込みのリスクを軽減。
- 環境変数の扱い:
  - .env 読み込み時に OS 環境変数を保護する protected セットを導入し、意図しない上書きを防止。

---

注: 本リリースはコア基盤（データ取得/保存、ETL 土台、ニュース収集、設定管理、DB スキーマ）を提供します。戦略実装、発注実行ロジック、監視機能の詳細実装は今後のバージョンで追加予定です。