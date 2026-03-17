# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記載しています。  
この CHANGELOG は、与えられたコードベースの内容から推測して作成しています。

フォーマット: 
- Unreleased — 今後の予定/注意点
- 各リリースは日付付きで記載（YYYY-MM-DD）

## [Unreleased]
- ドキュメント整備: API 使用例・運用手順・DataPlatform/Schema ドキュメントとのリンクを追加予定
- テスト拡充: ネットワーク周り（SSRF/リダイレクト/大容量レスポンス）、.env パーサ、ETL ワークフローの統合テストを追加予定
- ETL パイプライン: run_prices_etl の継続実装（財務データ・カレンダーの差分ETL、品質チェックのフロー統合）とモニタリング/アラートの追加予定
- パフォーマンス改善: DuckDB のバルク挿入パラメータ調整や並列フェッチ戦略の検討
- 安全性/運用改善: 機密情報の取り扱い・ロギングの更なる最小化（トークンやシークレットの漏洩防止）

---

## [0.1.0] - 2026-03-17
最初の公開リリース（推定）。以下の主要機能・設計方針を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0, __all__ の定義）。
- 設定管理 (kabusys.config)
  - .env / 環境変数読み込み機能を実装（自動ロード: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ: export 形式、クォート/エスケープ、インラインコメントの取り扱いに対応。
  - OS 環境変数を保護する protected モード（.env.local 上書きの際に元の OS 環境を保護）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス 等のプロパティを取得可能に。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。
- J-Quants クライアント (kabusys.data.jquants_client)
  - API ラッパーを実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - リトライ戦略: 指数バックオフ、最大 3 回リトライ、408/429/5xx を再試行対象に。
  - 401 受信時の自動 ID トークンリフレッシュ（1 回のみ）と再試行を実装。
  - ページネーション対応（pagination_key を使った繰り返し取得）。
  - データ保存時に取得時刻(fetched_at)を UTC で記録して Look-ahead Bias を低減。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE により冪等性を確保。
  - 数値変換ユーティリティ (_to_float, _to_int) を実装（不正値に対する寛容な処理）。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得する fetch_rss、記事前処理、記事保存、銘柄紐付けの統合ジョブを実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
  - セキュリティ対策:
    - defusedxml を利用して XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/IP のプライベート判定、リダイレクト時の事前検査用ハンドラを実装。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズチェックを導入（メモリ DoS 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保持。
  - raw_news へのバルク挿入はチャンク化してトランザクションで実行、INSERT ... RETURNING を使い実際に挿入された ID を返す。
  - news_symbols（記事と銘柄の紐付け）をチャンク化して ON CONFLICT DO NOTHING + RETURNING で保存。
  - 銘柄コード抽出ロジック（4桁数字で known_codes によるフィルタ）を実装。
  - テキスト前処理関数（URL 除去、空白正規化）を提供。
- DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル定義を作成。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等 Feature 層のテーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等 Execution 層のテーブルを定義。
  - 制約（NOT NULL / CHECK / FOREIGN KEY / PRIMARY KEY）を多用してデータ品質を担保。
  - 頻出クエリに備えたインデックス群を作成。
  - init_schema(db_path) でディレクトリ作成→テーブル作成→インデックス作成を行う冪等な初期化 API を提供。
  - get_connection(db_path) で既存 DB へ接続する API を提供。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新のためのユーティリティ（テーブル存在チェック、最大日取得、営業日調整）を実装。
  - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーの集約）。
  - run_prices_etl を実装（差分算出、バックフィル日数指定、J-Quants からの取得→DuckDB への保存）。※財務・カレンダー周りの ETL は同様の設計で実装予定。
  - デフォルトのバックフィル日数: 3 日、カレンダー先読み: 90 日、最小データ日: 2017-01-01 を考慮。

### 変更 (Changed)
- 初期リリースのため該当なし（設計・実装の全体は新規追加）。

### 修正 (Fixed)
- 初期リリースのため該当なし（バグ修正履歴は今後追記予定）。

### セキュリティ (Security)
- XML パースに defusedxml を利用し XML 関連攻撃を軽減。
- RSS フェッチにおいてスキーム検査、ホストのプライベート判定、リダイレクト時の検査を実装し SSRF を防止。
- .env の自動読み込みでは OS 環境を保護する仕組みを導入（.env が OS 環境を上書きしない既定動作等）。
- ネットワークリトライやログ出力時にトークン等が漏れないよう、リフレッシュは内部キャッシュ管理で実装。

---

備考:
- 本 CHANGELOG は与えられたソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに基づいて更新してください。