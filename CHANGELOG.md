# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）の現状から推測して作成した初期リリース向けの変更履歴です。

全般的な注意:
- バージョンはパッケージ定義 (kabusys.__version__ = "0.1.0") に基づいています。
- 以下の記載はソースコードの内容から推測した機能・設計方針・既知の注意点を含みます。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期化
  - kabusys パッケージの基本構成を追加。__version__ を "0.1.0" に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により作業ディレクトリに依存しない読み込みを実現。
  - .env/.env.local の読み込み優先度を実装（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化機能を追加（テスト用）。
  - 強力な .env 行パーサー（export 形式・クォート・インラインコメントの扱いに対応）。
  - Settings クラスを提供し、J-Quants トークン、Kabu API パスワード、Slack トークン、DB パス、環境モード（development/paper_trading/live）などのプロパティ経由で取得可能。
  - env / log_level の検証（許容値チェック）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を追加（ページネーション対応）。
  - HTTP レート制御（120 req/min 固定間隔スロットリング）を _RateLimiter で実装。
  - 冪等保存用の save_* 関数を追加（DuckDB への INSERT ... ON CONFLICT DO UPDATE を使用）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 応答時は自動で ID トークンをリフレッシュして 1 回のみリトライする仕組みを実装。
  - ID トークンのモジュールレベルキャッシュを導入し、ページネーション間で共有して API 呼び出しを効率化。
  - JSON デコードエラーやネットワークエラーのハンドリングとログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得する fetch_rss を実装（デフォルトソースあり: Yahoo Finance）。
  - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先のスキーム・ホストを検証する専用ハンドラ（_SSRFBlockRedirectHandler）。
    - ホスト名の DNS 解決後に IP を検査し、プライベート/ループバック/リンクローカルなどへのアクセスを拒否。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェックを導入（メモリ DoS / Gzip bomb 対策）。
  - URL 正規化（トラッキングクエリパラメータ除去、フラグメント削除、クエリソート）と SHA-256 を用いた記事 ID 生成（先頭32文字）で冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - raw_news テーブルへのバルク挿入（INSERT ... RETURNING）を実装し、挿入された新規記事 ID リストを返す機能を追加。
  - news_symbols テーブルへの銘柄紐付け（単一記事・一括）を実装。チャンク処理とトランザクションを用いた安全な保存。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用の完全なスキーマを追加（Raw / Processed / Feature / Execution 層を包含）。
  - raw_prices、raw_financials、raw_news、raw_executions、prices_daily、market_calendar、fundamentals、news_articles、news_symbols、features、ai_scores、signals、signal_queue、orders、trades、positions、portfolio_performance 等のテーブル定義を実装。
  - 適切な CHECK 制約、PRIMARY KEY、FOREIGN KEY を含むDDLを提供。
  - 頻出クエリ向けの INDEX 定義を追加。
  - init_schema(db_path) でディレクトリ作成からテーブル作成・インデックス作成まで全自動初期化を実装。get_connection() で既存 DB への接続を提供。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL 実行結果を表す ETLResult データクラスを実装（品質問題・エラーログの収集を含む）。
  - 差分更新ロジック用ユーティリティ（テーブル存在確認、最大日付取得、営業日補正）を実装。
  - run_prices_etl の骨組みを追加（差分算出、backfill の考慮、jquants_client 経由で取得→保存）。
  - 市場カレンダー先読み日数やバックフィル日数の定数化。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- RSS パーサーで defusedxml を利用し XML 関連攻撃を低減。
- SSRF 対策強化（スキーム検証、リダイレクト時の検査、プライベートIP検出）。
- .env の扱いで OS 環境変数を保護する仕組みを導入（override の挙動制御）。

### Performance
- API 呼び出しに対する固定間隔レートリミッタを導入し、J-Quants のレート制限を守る設計。
- ID トークンキャッシュにより不必要なトークン取得を削減。
- ニュース保存処理はチャンク単位でのバルクINSERTとトランザクションまとめにより DB オーバーヘッドを低減。
- DuckDB スキーマに頻出クエリ向けのインデックスを追加。

### Notes / Known issues（推測）
- ETL パイプライン（kabusys.data.pipeline）は基盤と主要ヘルパーを実装済みだが、品質チェック（quality モジュールとの連携）や価格 ETL の最終的な戻り値/後続処理の統合は継続実装が想定される（コードスニペットの切れ目から一部処理や戻り値の整合性確認が必要）。
- strategy、execution、monitoring サブパッケージはパッケージ下に存在するが（__init__.py が空の状態）、主要ロジックはまだ未実装または別モジュールで実装予定。
- オンライン API を利用する箇所は外部依存（J-Quants、各 RSS ソース、Kabu API 等）があるため、本番環境での運用には適切なシークレット管理・環境設定・リトライ/監視設定の追加を推奨。

---

今後のリリースで想定される作業例（参考）
- pipeline の完結（品質チェック結果の ETLResult への反映、calendar/fundamentals ETL の統合）。
- strategy / execution ロジックの実装（シグナル生成・発注・約定トラッキング）。
- monitoring（Slack 通知など）との統合。
- テストカバレッジの強化（ネットワーク関連のモック、DB のインメモリテスト等）。
- ドキュメント（使用例、API レート設計・運用ガイド）の充実。

（以上）