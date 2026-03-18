# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Known issues / 注意点
- run_prices_etl の戻り値が仕様どおり (fetched, saved) のタプルになっていない箇所が存在します（prices_saved が返されない/未完成）。ETL 呼び出し側で期待される値と不整合になる可能性があるため修正を推奨します。
- 一部モジュール（execution, strategy パッケージなど）は初期のプレースホルダで、実装が薄い／未実装の機能があります。

---

## [0.1.0] - 2026-03-18

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージトップ: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義、公開モジュールを __all__ で列挙（data, strategy, execution, monitoring）。
- 設定/環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサが export プレフィックス、シングル/ダブルクォート、インラインコメント等を正しく扱うよう実装。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パスなどの必須／既定値を取得可能に。値検証 (KABUSYS_ENV, LOG_LEVEL) を実装。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（レートリミッタ、リトライ、401 自動リフレッシュ、ページネーション対応）。
  - 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ: 指数バックオフ（最大 3 回）、408/429/5xx を対象。429 の場合は Retry-After を尊重。
  - 401 受信時は ID トークンを自動更新して 1 回リトライ（無限再帰回避のため allow_refresh フラグを導入）。
  - データ取得関数を追加: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数を追加: save_daily_quotes, save_financial_statements, save_market_calendar。取得時刻（fetched_at）を UTC で記録し、INSERT は ON CONFLICT DO UPDATE により冪等化。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事収集する機能を実装（DEFAULT_RSS_SOURCES に Yahoo Finance を含む）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検査、リダイレクト時の事前検証ハンドラを独自実装。
    - レスポンス受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化機能を実装: トラッキングパラメータ（utm_*, fbclid 等）の除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - RSS 取得処理 fetch_rss を実装（タイトル/本文の前処理、pubDate パース、content:encoded 優先処理）。
  - DB 保存: save_raw_news（チャンク化・トランザクション・INSERT ... RETURNING による実挿入件数取得）、news_symbols 紐付け処理（bulk 処理、ON CONFLICT DO NOTHING）。
  - 銘柄コード抽出ロジックを実装（4桁の数字、known_codes によるフィルタ、重複除去）。
- DB スキーマ初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく DuckDB スキーマを実装。3 層（Raw / Processed / Feature）+ Execution レイヤーを定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）および実務的な型を定義。
  - インデックス群（頻出クエリを想定した複合インデックス等）を作成。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行し接続を返す。get_connection で既存 DB へ接続。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針に基づく差分更新処理群の下地を実装。
  - ETLResult dataclass: ETL 実行結果（取得件数・保存件数・品質問題・エラー）を表現。品質問題を辞書化する to_dict を提供。
  - 差分更新ユーティリティ: テーブル存在チェック、最大日付取得ヘルパ、トレーディング日調整（市場カレンダー参照）を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl を実装（差分算出、バックフィル default 3 日、fetch + save の流れ）。※ただし前述のとおり戻り値整合の問題があるため注意。
  - 定数: API が提供する最小データ日 _MIN_DATA_DATE、カレンダー先読み日数 _CALENDAR_LOOKAHEAD_DAYS など。
  - 品質チェックモジュール quality との連携点（QualityIssue を扱う設計）を確立（実行は quality モジュール依存）。
- その他
  - モジュール構成の骨格（data, strategy, execution, monitoring）を作成し、今後の実装に備える。

Security
- defusedxml による XML パース、SSRF 対策、外部コンテンツ受信時のサイズ上限、gzip 解凍後サイズ検査などセキュリティに配慮した実装を多数導入。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed / Deprecated
- 初期リリースのため該当なし。

Notes / その他
- DuckDB をメインの分析 DB として採用し、ON CONFLICT（冪等）や INSERT ... RETURNING（実挿入数の正確取得）を多用しているため、並行実行性やトランザクション処理の設計に注力されています。
- 外部 API 呼び出し部は urllib ベースで実装されており、トークンキャッシュや retry/バックオフ、pagination の取り扱いなど実運用を想定した堅牢な実装方針が取られています。
- 今後の作業候補:
  - run_prices_etl の戻り値の不整合修正（prices_saved を確実に返す）。
  - strategy / execution / monitoring の具象実装。
  - 単体テスト・統合テストの追加（ネットワーク依存部はモック化してテスト可能な設計がなされている）。
  - quality モジュールの具体的実装と ETL への組み込み強化。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。必要であれば各変更項目の詳細（該当ファイル・行番号・例）を付けた拡張版を作成します。