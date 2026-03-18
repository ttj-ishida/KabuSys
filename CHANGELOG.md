# CHANGELOG

このファイルは Keep a Changelog の形式に準拠します。  
重要な変更点はすべてここに記載します。セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージの初期リリース。
- 基本パッケージ構成を追加:
  - kabusys.config: 環境変数／.env 管理（自動ロード、.env/.env.local の優先順、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - kabusys.data: データ取得・保存関連モジュール群（jquants_client, news_collector, schema, pipeline）。
  - kabusys.strategy, kabusys.execution, kabusys.monitoring のプレースホルダモジュールを追加。
- 環境設定 (Settings) クラス:
  - J-Quants / kabuAPI / Slack / DB パス等の設定プロパティを実装。
  - KABUSYS_ENV / LOG_LEVEL の値検証（allowed 値のチェック）と利便性プロパティ（is_live / is_paper / is_dev）を提供。
  - デフォルト値（例: KABUSYS_API_BASE_URL、DUCKDB_PATH, SQLITE_PATH）を定義。

- J-Quants API クライアント (kabusys.data.jquants_client):
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得関数を実装（ページネーション対応）。
  - レート制御（固定間隔スロットリング）で 120 req/min を順守する RateLimiter を導入。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx をリトライ対象に設定。
  - 401 受信時にリフレッシュトークンを自動更新して 1 回再試行する処理を実装（再帰防止）。
  - ID トークンのモジュールレベルキャッシュを実装し、ページネーション呼び出し間で共有。
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）を提供。
  - 型変換ユーティリティ（_to_float, _to_int）を実装。

- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィード取得・パース機能を実装（defusedxml 使用）。
  - 記事IDを正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、フラグメント除去、クエリソートを実施。
  - SSRF 対策: スキーム検証（http/https のみ）、ホストのプライベート IP 判定、リダイレクト先検査（カスタム RedirectHandler）。
  - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存は INSERT ... RETURNING を使用し、新規挿入された記事IDを返す実装（チャンク処理、トランザクション単位での一括挿入）。
  - 記事と銘柄コードの紐付け（news_symbols）の一括保存ロジックを実装（重複排除、チャンク挿入、RETURNING）。

- スキーマ定義 (kabusys.data.schema):
  - DuckDB 用の包括的なスキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルや、prices_daily, market_calendar, fundamentals, features, ai_scores, signals, orders, trades, positions 等を定義。
  - 外部キー考慮のテーブル作成順、実運用での検索を想定したインデックス群を定義。
  - init_schema(db_path) で必要な親ディレクトリ作成→DDL 実行→接続を返すユーティリティを提供。get_connection で既存 DB に接続可能。

- ETL パイプライン基盤 (kabusys.data.pipeline):
  - 差分更新戦略（最終取得日からの差分・バックフィル）を想定した ETL の骨組みを実装。
  - ETL 実行結果を表す ETLResult データクラス（品質問題・エラー集約とユーティリティ）を提供。
  - 市場カレンダーの先読みや、営業日調整ヘルパーを実装。
  - raw_* の最終日取得ユーティリティ（get_last_price_date 等）を提供。
  - run_prices_etl など個別 ETL ジョブの骨子を実装（差分算出、fetch → save の流れ）。

### 改善 (Changed)
- なし（初期リリースのため）。

### 修正 (Fixed)
- なし（初期リリースのため）。

### セキュリティ (Security)
- RSS XML 解析に defusedxml を採用し XML Bomb 等の攻撃に対処。
- SSRF 緩和策を多数導入:
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定し拒否。
  - リダイレクト時に検査するカスタム RedirectHandler を使用。
- HTTP レスポンスサイズを上限（10MB）で検査し、gzip 解凍後もサイズ確認。

### パフォーマンス (Performance)
- J-Quants API 呼び出しで固定間隔の RateLimiter を導入しレートリミットを厳守。
- リトライ時は指数バックオフ、429 時は Retry-After ヘッダを優先。
- news_collector の DB 保存はチャンク化・一括 INSERT（RETURNING）でオーバーヘッドを削減。
- news_symbols の一括挿入で重複を除去して無駄な挿入を抑制。

### 互換性 / 移行注意点 (Notes)
- DB 初期化は init_schema() を必ず呼び出してから運用してください。既存 DB に対しては get_connection() を使用。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テスト等で自動ロードを無効化する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の認証はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。設定がない場合は Settings のプロパティが ValueError を投げます。
- news_collector の URL 正規化や記事IDの生成・重複許容のルールに依存するため、既存の外部記事IDベースの運用がある場合は注意してください。

---

今後の予定（例）:
- strategy / execution / monitoring の実装拡張（現状はパッケージ初期プレースホルダ）。
- 品質チェックモジュール (kabusys.data.quality) の実装完了とパイプライン統合。
- テストカバレッジ拡充、外部 API 呼び出しのモック化用ユーティリティの追加。