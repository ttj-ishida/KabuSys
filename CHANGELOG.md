# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

履歴は SemVer に準拠しています。（現在のパッケージバージョン: 0.1.0）

---

## [0.1.0] - 2026-03-17

初回リリース。本リリースで導入された主な機能・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を定義。
  - `kabusys` パッケージの公開モジュール一覧を `__all__` で宣言（data, strategy, execution, monitoring）。

- 環境設定管理 (`kabusys.config`)
  - `.env` ファイルまたは環境変数から設定を読み込む `Settings` クラスを提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml 基準）を探索して `.env` / `.env.local` を読み込み。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能（テスト向けフック）。
  - `.env` のパースは `export KEY=val` 形式・クォートやインラインコメント対応。
  - 必須環境変数取得用 `_require` と、設定項目のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
  - 既定値を持つ設定: Kabu API ベース URL、DuckDB/SQLite のデータパス等。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する機能を実装。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制限（内部 RateLimiter）。
  - リトライと指数バックオフ: ネットワークエラーや 408/429/5xx を最大 3 回リトライ、429 の場合は `Retry-After` を優先。
  - 401 Unauthorized 時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ化（ページネーション連続呼び出しで共有）。
  - ページネーション対応の取得関数（fetch_* 系）。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を利用）を提供。
  - 数値変換ユーティリティ `_to_float` / `_to_int` を実装（安全な変換方針を採用）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を収集して `raw_news` テーブルへ冪等保存する機能を提供。
  - セキュリティ対策: defusedxml による XML パース、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍後の再検査。
  - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム/ホスト事前検査、プライベート/ループバック/リンクローカルアドレス判定。
  - 記事ID は URL 正規化後の SHA-256 の先頭 32 文字で生成（utm_* 等のトラッキングパラメータを除去）。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存: チャンク（デフォルト 1000 件）でのバルク INSERT、トランザクションでまとめて保存、INSERT ... RETURNING を用いて実際に挿入された ID を返す。
  - 銘柄コード抽出: 本文・タイトルから 4 桁銘柄コードを抽出し、既知コードセットでフィルタ。news_symbols テーブルへ紐付けをバルクで保存。

- DuckDB スキーマ & 初期化 (`kabusys.data.schema`)
  - DataPlatform に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores（Feature 層）および signals, signal_queue, orders, trades, positions, portfolio_performance（Execution 層）。
  - 各種チェック制約（CHECK）、外部キー、インデックスを定義。
  - `init_schema(db_path)` により DB ファイルの親ディレクトリを自動作成してテーブルを冪等に作成。
  - `get_connection(db_path)` で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新型の ETL 実装方針を導入。
  - 最終取得日に基づく差分取得、デフォルトのバックフィル日数（3 日）により後出し修正を吸収。
  - 市場カレンダーの先読み（90 日）や、初回ロード時の開始日設定（2017-01-01）。
  - ETL 実行結果を表す `ETLResult` dataclass（品質問題やエラーの集約、辞書化機能含む）。
  - テーブル存在チェック、最大日付取得、営業日に調整するヘルパーなどを提供。
  - 個別 ETL ジョブ（run_prices_etl 等）の骨組みを実装（差分算出・取得・保存・ログ）。

### 変更 (Changed)
- （初版につき履歴なし）

### 修正 (Fixed)
- （初版につき既存修正なし）

### セキュリティ & 信頼性強化
- XML パースに defusedxml を利用し XML-Bomb 等の攻撃を軽減。
- RSS フェッチで Content-Length の事前チェックと読み取り長の上限を設け、メモリ DoS を防止。
- リダイレクト毎にスキームとホスト検証を行い SSRF を軽減。
- J-Quants クライアントはトークン自動リフレッシュ時の無限再帰を防止するフラグ（allow_refresh=False）を導入。

### その他の実装上の注記・拡張ポイント
- `kabusys.config` の .env パーサは shell 風の export 指定、クォート、インラインコメント等にある程度対応する実装となっていますが、完全な dotenv 互換ではありません。プロジェクト配布後もファイル位置を探索するために __file__ を基点とする設計です。
- `kabusys.data.news_collector._urlopen` はテスト容易性のためにモック差し替え可能な実装になっています。
- `execution` / `strategy` / `monitoring` サブパッケージはパッケージ構成上存在しますが、このリリースのコードでは初期化ファイルのみ（中身未実装）です。今後の実装対象。

---

今後の予定（例）
- execution / strategy の実装（注文送信・約定管理・戦略実行ループ）
- 品質チェックモジュール（quality）の実装と ETL における詳細なレポーティング
- 単体テスト・統合テストの充実、CI ワークフローの整備

---

参考: 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリース・機能要件と差異がある場合は差し替えてください。