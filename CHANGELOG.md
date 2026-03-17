# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトの初版リリース履歴を示します。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤機能を実装。
  - パッケージメタ情報 (src/kabusys/__init__.py) にバージョン `0.1.0` を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で自動ロード。
  - .env/.env.local の読み込み順序、OS環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env 行パーサ（export 構文、クォート処理、インラインコメントルールに対応）。
  - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DBパス、環境種別・ログレベルの検証等）。
  - 環境値検証（KABUSYS_ENV と LOG_LEVEL の許容値チェック、必須項目の未設定時に明確なエラー）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
  - レート制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を用いて重複更新を抑制。
  - 再試行ロジック: 指数バックオフ（最大試行回数 3 回）、408/429/5xx に対する再試行、429 の Retry-After 優先処理。
  - 401 発生時のトークン自動リフレッシュ（1 回だけ行う安全な挙動）およびモジュールレベルの ID トークンキャッシュ共有。
  - ページネーション対応の fetch_* 関数（pagination_key の重複防止）。
  - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は fetched_at を UTC で記録。
  - 型変換ユーティリティ（文字列→float/int）の頑健化。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得から raw_news テーブルへの冪等保存を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベート/ループバック/リンクローカル/マルチキャストアドレスへの接続拒否、リダイレクト先の事前検査（カスタム RedirectHandler）。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES＝10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）と SHA-256（先頭32文字）による記事ID生成。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース（UTC への正規化、失敗時は警告と現在時刻で代替）。
  - DB 保存の実装:
    - save_raw_news: チャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDを返す。トランザクションを用いた一括挿入。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING で挿入数を正確に把握）。
  - 銘柄抽出機能: テキストから 4 桁の銘柄コード抽出し、既知銘柄セットでフィルタリング。

- データベーススキーマ管理 (src/kabusys/data/schema.py)
  - DuckDB 用のデータスキーマを定義・初期化する init_schema 関数を提供。
  - 3 層データモデル（Raw / Processed / Feature / Execution）に対応する多数のテーブル定義を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを定義してパフォーマンスとデータ整合性を確保。
  - init_schema は父ディレクトリの自動作成や :memory: 対応をサポート。get_connection による接続取得も提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づく差分更新（最終取得日からの差分算出）、バックフィル（デフォルト 3 日）、市場カレンダー先読み等のヘルパーを実装。
  - ETL 実行結果を表す ETLResult dataclass（品質問題やエラー情報を含む）を実装。品質チェックの重大度判定（has_quality_errors）や辞書化メソッドを提供。
  - テーブル存在チェック、最大日付取得、営業日調整等のユーティリティ関数を実装。
  - run_prices_etl（差分 ETL）の骨組みを実装（fetch → save の流れ、date_from 自動算出、保存結果返却）。

### Changed
- （初版のため過去からの変更はなし）初期設計において以下の設計方針を明確化:
  - 冪等性を重視した DB 保存（ON CONFLICT の使用）。
  - テスト容易性のために id_token 注入や _urlopen のモック可能化を考慮。
  - ハードニング（SSRF、XML/ZIP 攻撃、メモリ DoS）に配慮した実装。

### Fixed
- （初版）実行時に想定されるエラー条件に対してログ出力と例外処理を含め、失敗時でも他処理に影響を与えない堅牢な設計を採用。

### Security
- RSS / HTTP 周りに対する複数のセーフガードを導入:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム検証・プライベートアドレス拒否・リダイレクト前検査）。
  - レスポンスサイズ制限および gzip 解凍後のサイズ検査（Gzip bomb 対策）。

---

注記:
- この CHANGELOG はコードベースから推測して作成した初回リリースの要約です。将来的に機能追加・修正が行われた際は、Keep a Changelog のルールに従って追記してください。