# Changelog

全ての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-17

### 追加
- パッケージ初期公開: `kabusys` 基本モジュールを追加。
  - パッケージ公開情報: `src/kabusys/__init__.py`（バージョン: 0.1.0、エクスポート: data, strategy, execution, monitoring）
  - 空のプレースホルダモジュール: `strategy`, `execution`, `monitoring`（将来的な戦略・発注・監視機能の拡張ポイント）
- 環境設定管理モジュールを追加（`src/kabusys/config.py`）。
  - .env 自動読み込み機能（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - 読み込み順序: OS 環境 > .env.local（上書き） > .env（非上書き）。
  - `.env` 解析の強化: export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 必須値チェック（`_require`）と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス等のプロパティを取得できる。
  - `KABUSYS_ENV` / `LOG_LEVEL` の値検証、環境判定ヘルパー（is_live / is_paper / is_dev）。
- J-Quants API クライアントを追加（`src/kabusys/data/jquants_client.py`）。
  - データ取得機能:
    - 株価日足（OHLCV）取得（ページネーション対応）
    - 財務データ（四半期 BS/PL）取得（ページネーション対応）
    - JPX マーケットカレンダー取得
  - 実装上の特徴:
    - API レート制御: 固定間隔スロットリング（120 req/min を守る RateLimiter）。
    - リトライ/バックオフ: 指数バックオフ、最大 3 回、408/429/5xx を再試行対象。
    - 401 時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション跨ぎで利用）。
    - JSON デコードエラーやネットワーク例外の扱いを明確にログ出力。
    - DuckDB へ保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を用意。冪等性を考慮した SQL（ON CONFLICT DO UPDATE）で重複を排除。
    - データ型変換ユーティリティ（_to_float / _to_int）を提供し不正値を安全に扱う。
- ニュース収集モジュールを追加（`src/kabusys/data/news_collector.py`）。
  - RSS フィードからのニュース取得・前処理・DB 保存のフローを実装。
  - セキュリティ・堅牢性:
    - defusedxml を使用した XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト時の事前検査（カスタム RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 対策、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化でトラッキングパラメータ除去（utm_* 等）とハッシュ化による記事 ID 生成（SHA-256 の先頭32文字）で冪等性を実現。
  - 取得・保存機能:
    - fetch_rss: RSS 取得と記事（NewsArticle）生成。content:encoded の優先採用、pubDate パース、title/content の前処理（URL除去・空白正規化）。
    - save_raw_news: DuckDB の raw_news にチャンク分割・トランザクションで保存。INSERT ... ON CONFLICT DO NOTHING RETURNING id により新規挿入IDのみを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（チャンク、トランザクション、ON CONFLICT DO NOTHING）。
    - 銘柄コード抽出ロジック（4桁数字パターン + known_codes によるフィルタ）。
    - run_news_collection: 複数 RSS ソースを走査して DB 保存し、新規保存数の集計まで実行。ソース毎に独立してエラーハンドリング。
- DuckDB スキーマ定義モジュールを追加（`src/kabusys/data/schema.py`）。
  - Raw / Processed / Feature / Execution 層のテーブル定義を含む DDL を提供。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各種制約・チェック制約を定義（NULL/PK/チェック制約、外部キー等）。
  - よく使うクエリ向けのインデックスも作成。
  - init_schema(db_path) でディレクトリの自動作成→全テーブル・インデックスを作成する初期化処理を提供。get_connection() で既存 DB への接続を取得。
- ETL パイプライン基盤を追加（`src/kabusys/data/pipeline.py`）。
  - ETLResult dataclass による ETL 実行結果の集約（品質問題・エラー一覧を格納、辞書化可能）。
  - 差分更新のためのヘルパー関数（_table_exists、_get_max_date、get_last_price_date、get_last_financial_date、get_last_calendar_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl: 差分取得ロジック（最終取得日から backfill_days を用いた再取得、期間指定）、J-Quants クライアント呼び出しと save を組み合わせた ETL 実装（取得→保存→ログ）。バックフィルと差分取得の設計を実装。
  - ETL の設計方針として品質チェック（quality モジュール）との連携を想定（品質問題は収集を継続し呼び出し側で判断）。

### セキュリティ
- RSS パーサーに defusedxml 採用、SSRF 対策、レスポンスサイズ制限、Gzip bomb 対策など複数の防御層を実装。
- .env パーサーでのクォート/エスケープ対応やコメント処理により意図しない値の誤解釈を軽減。

### 性能 / 信頼性
- J-Quants クライアント:
  - レート制御（120 req/min）やトークンキャッシュで API レートや認証の安定化を図る。
  - 再試行と指数バックオフで一時的障害に耐性を持たせる。
- ニュース収集:
  - チャンク化（_INSERT_CHUNK_SIZE）・トランザクション・INSERT RETURNING により大量データ挿入時のオーバーヘッドを削減しつつ正確な新規挿入数を取得。
- DuckDB スキーマに制約とインデックスを用意し、データ整合性とクエリ性能に配慮。

### 既知の制限 / 注意点
- strategy / execution / monitoring モジュールはプレースホルダとして存在しており、実際の戦略ロジックや注文実行ロジックは含まれていない（今後の実装予定）。
- pipeline.run_prices_etl は設計方針・差分取得を実装しているが、quality モジュールとの結合や他の ETL ジョブ（財務・カレンダー等）との統合テストは今後整備が必要。
- DuckDB を使った SQL 実行ではプレースホルダ連結を文字列生成で行う箇所があり（INSERT のプレースホルダ構築）、将来的に SQL インジェクション対策・ライブラリの機能に合わせた実装見直しが必要かもしれない（現状は内部利用前提）。

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### 削除
- （初版のため該当なし）

---

今後の予定（例）
- strategy モジュールに戦略実装を追加（特徴量→シグナル生成→ポートフォリオ最適化）。
- execution モジュールで kabuステーション等への発注・注文管理機能を実装。
- monitoring モジュールで Slack 通知や監視アラートを追加。
- ETL の統合テスト、品質チェック（quality モジュール）ルールの実装と自動化。