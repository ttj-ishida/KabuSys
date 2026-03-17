# CHANGELOG

すべての変更は Keep a Changelog の慣習に従い、Semantic Versioning を想定しています。  
注: 以下の変更履歴は提供されたコードベースの内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初期リリース — 日本株自動売買システム「KabuSys」のコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの基本（src/kabusys/__init__.py）。バージョン番号を "0.1.0" として公開。
  - パッケージ API として data, strategy, execution, monitoring を公開。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルまたは環境変数からの設定読み込みを実装。プロジェクトルート判定に .git / pyproject.toml を使用し、CWD に依存しない自動ロードを実現。
  - .env パーサー実装（コメント行・export 形式・クォート・エスケープ・インラインコメント処理対応）。
  - 自動ロード制御フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - settings オブジェクトを提供し、J-Quants / kabuステーション / Slack / DB パス / システム環境（development / paper_trading / live）などのプロパティを取得可能。
  - 環境変数必須チェック用の _require を実装し不足時は ValueError を送出。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ベース実装: ID トークン取得、株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
  - RateLimiter によるレート制限（120 req/min, 固定間隔スロットリング）を実装。
  - 冪等保存用の DuckDB 保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複回避。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装。429 の場合は Retry-After ヘッダを尊重。
  - 401 受信時にはリフレッシュトークンで自動的に id_token を再取得して 1 回だけリトライする仕組みを実装（無限再帰回避のため allow_refresh 制御あり）。
  - ページネーション対応。ページネーションキーの重複を検知してループ終了。
  - 取得時の fetched_at を UTC ISO8601 で付与し、Look-ahead Bias のトレースを可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS からのニュース収集と DuckDB への冪等保存機能を実装（raw_news / news_symbols）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
    - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査用のカスタムハンドラ）。
    - URL スキームは http/https のみ許可。
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を設定して取得。
  - 記事IDは URL 正規化（トラッキングパラメータ削除・ソート・フラグメント除去など）後に SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理（URL除去、空白正規化）を実装。
  - 銘柄コード抽出（4桁数字パターン）と既知銘柄セットによるフィルタリング機能を提供。
  - DB 側の保存はチャンク・トランザクション単位で行い、INSERT ... RETURNING を用いて実際に挿入された件数を返却。
  - デフォルト RSS ソースとして Yahoo Japan のビジネスカテゴリを登録。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に分けたテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス定義を含むDDLを提供。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成・テーブル作成を行い、接続を返す。get_connection() で既存 DB 接続を取得可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新の考え方を実装（最終取得日を参照し backfill_days により数日前から再取得）。
  - run_prices_etl 等、個別 ETL ジョブの骨組みを実装。取得 → 保存（jquants_client） → 品質チェック（quality モジュール想定）というフローを想定。
  - ETL 実行結果を表す ETLResult dataclass を実装（品質問題・エラーの集約、辞書化対応）。
  - DB 存在チェック、最大日付取得、営業日調整処理などのヘルパー関数を実装。
  - J-Quants API 呼び出しに id_token 注入可能でテスト容易性を確保。

- ユーティリティ関数
  - データ安全な変換ユーティリティ（_to_float, _to_int）を実装し、空文字列や不正値を None に変換して上流処理を安定化。
  - RSS 日時パース（RFC 2822 互換）とフォールバック実装（パース失敗時は警告ログと現在時刻代替）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- RSS および HTTP 取得に関する複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 対策（ホストのプライベートIP検出、リダイレクト先検査、許可スキーム制限）。
  - レスポンスサイズ上限と Gzip 解凍後のサイズチェックによる DoS 緩和。
  - 外部入力（.env ファイル）の安全なパース（クォート・エスケープ処理、コメント処理）。

### Notes
- jquants_client の HTTP 層は urllib を用いた実装。ID トークンのキャッシュと自動リフレッシュ、リトライ戦略が組み込まれている。
- news_collector はネットワーク層をモック差し替え可能（_urlopen の置換）な設計になっており、テストの容易性を考慮。
- schema.init_schema() は :memory: をサポートし、ローカルファイル作成時は親ディレクトリを自動生成する。
- pipeline モジュールは ETL の主要ロジックを含むが、品質チェックや一部の細かい統合処理（quality モジュールや上位ジョブの完全な実装）は別モジュールに依存しており、今後の拡張点となる。

---

将来のリリースでは、Strategy / Execution 層の具体実装（取引実行用のラッパーや注文管理の連携）、監視/アラート機能（Slack 通知等）、品質チェックモジュールの詳細実装とテスト、CI による自動 schema 適用などを予定しています。