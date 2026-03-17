# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。  

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。主要なモジュールと機能を実装しました。

### Added
- パッケージ初期化
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。公開モジュールとして data, strategy, execution, monitoring をエクスポート（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local からの自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export 付き行、クォート文字列、インラインコメント、トラッキングされた値など多様な .env 形式の堅牢なパースロジック。
  - OS 環境変数を保護する protected 機構、.env.local による上書き優先度。
  - 必須環境変数取得のユーティリティ（_require）と Settings クラス（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル等のプロパティ）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務情報（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - API レート制御（120 req/min）を固定間隔スロットリングで実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）と 429 の Retry-After 優先処理。
  - 401 受信時の ID トークン自動リフレッシュ（1回のみ）対応。
  - 取得時刻（fetched_at）を UTC（ISO Z 形式）で記録し Look-ahead bias のトレースに対応。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：ON CONFLICT による冪等なアップサート。
  - 型変換ユーティリティ（_to_float, _to_int）により不正値を安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集と raw_news/raw_news_symbols への保存処理を実装。
  - デフォルトソースとして Yahoo Finance のカテゴリRSSを設定。
  - URL 正規化（トラッキングパラメータ除去・クエリソート・フラグメント除去）と SHA-256 による記事 ID 生成（先頭32文字）。
  - defusedxml を使用した XML パース（XML Bomb 対策）。
  - SSRF 対策：
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時にスキーム・ホスト検査を行うカスタムハンドラ（_SSRFBlockRedirectHandler）
    - ホストがプライベート/ループバック/リンクローカルであれば拒否
  - レスポンスサイズ制限（10 MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去・空白正規化）と記事保存のチャンク化（INSERT ... RETURNING、トランザクション管理）によりメモリ・DB 性能を配慮。
  - テキストからの銘柄コード抽出（4桁コード、既知コードセットフィルタ）と一括紐付け保存関数。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を実装（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, orders, trades, positions, 等）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を定義。
  - 頻出クエリ向けのインデックス定義。
  - init_schema(db_path) にてディレクトリ作成を行い、全DDLを冪等に実行して接続を返す。get_connection() で既存DBへ接続。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分更新（最終取得日に基づく date_from 自動算出、デフォルトバックフィル 3 日）と市場カレンダーの先読みロジックを実装。
  - ETLResult dataclass による実行結果（取得数・保存数・品質問題・エラー）集約とシリアライズ。
  - テーブル存在チェック・最大日付取得などのユーティリティ。
  - run_prices_etl の雛形（差分ロジック・fetch/save 呼び出し）を実装（バックフィル考慮、取得と保存のログ記録）。

- 汎用的なログ出力・例外処理
  - 各処理での警告・情報ログを適切に出力。DB トランザクション失敗時のロールバックと例外再送出。

### Security
- ニュース収集における複数のセキュリティ対策を導入
  - defusedxml による XML 攻撃緩和
  - SSRF 対策（スキーム検査、プライベートIP検査、リダイレクト時の事前検査）
  - レスポンス最大バイト数制限・gzip 解凍後チェックによるメモリDoS対策

### Notes / Implementation details
- .env のパースはシェル風構文（export）、クォート、エスケープにある程度対応していますが、完全なシェル互換ではありません。
- J-Quants API の ID トークンはモジュールレベルでキャッシュされ、ページネーション処理間で共有されます。
- DuckDB への保存は基本的に ON CONFLICT を用いた冪等性を前提としています。
- pipeline モジュールは品質チェック用の quality モジュールインタフェースを想定しており、品質チェックは ETL を中断せずに収集結果を返す設計です。

### Known issues / TODO
- pipeline.run_prices_etl の末尾が実装途中の可能性（ドキュメント化や追加ジョブの統合は今後の作業）。
- strategy/ execution/ monitoring のパッケージがプレースホルダとして存在（実装未提供）。運用・発注ロジック・監視は今後追加予定。

---

(注) 上記はコードベースからの実装内容・設計意図をもとに作成した CHANGELOG です。将来的なリリースでは各項目をより詳細に分割（Added/Changed/Fixed/Security 等）して更新してください。