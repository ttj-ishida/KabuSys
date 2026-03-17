# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点・設計方針は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報とエクスポートを定義（kabusys.__init__）。
  - 空のモジュールプレースホルダを用意（kabusys.execution, kabusys.strategy）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
  - .env のパースロジックを実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト用）。
  - 重要設定取得のヘルパー（Settings クラス）を実装。必須キー未設定時は ValueError を送出。
  - env/log level の検証・ブールプロパティ（is_live/is_paper/is_dev）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本的な API 呼び出しユーティリティを実装（GET/POST、JSON デコード）。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大3回、408/429/5xx を再試行）。
  - 401 (Unauthorized) を受けた場合、リフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）は UTC で記録して Look-ahead Bias を抑制。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、空値や不正値を安全に扱う。

- ニュース収集（RSS）モジュール（kabusys.data.news_collector）
  - RSS フィードの取得・解析・正規化・DB 保存の一連処理を実装。
  - 記事IDは URL を正規化した上で SHA-256 の上位32文字を採用し冪等性を確保。
  - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、フラグメント除去、クエリソート等を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策：スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（DNS 解決による A/AAAA 検査）、リダイレクト時の事前検証用ハンドラ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 不正スキームやプライベートアドレスはログ出力のうえスキップ。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存はチャンク化・トランザクション化して一括 INSERT（ON CONFLICT DO NOTHING）し、実際に挿入された ID を返す（INSERT ... RETURNING を利用）。
  - 銘柄コード抽出ユーティリティ（4桁コード）と、記事と銘柄の紐付け保存関数を実装。
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection などの高レベル API を提供。
  - テスト容易性: ネットワーク呼び出し部分（_urlopen）を差し替え可能に設計。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を想定した包括的な DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols の Processed 層。
  - features, ai_scores の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - インデックス定義とテーブル作成順を定義し、init_schema() で安全に初期化（ディレクトリ自動作成・冪等）。
  - get_connection() で既存 DB への接続を取得。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL 実行結果を表す ETLResult データクラスを実装（品質問題リスト、エラー一覧、集計値）。
  - テーブル存在チェック、最大日付取得ユーティリティを実装。
  - 市場カレンダーを参照して非営業日を直近営業日に調整するヘルパーを実装。
  - 差分更新ロジック（最終取得日からの backfill 処理）を実装。
  - run_prices_etl を実装（date_from 自動算出、fetch -> save の流れ）。quality モジュールと連携する設計を想定。

### 変更 (Changed)
- 該当なし（初回リリースのため既存差分はなし）。

### 修正 (Fixed)
- 該当なし（初回リリースのため既存バグ修正履歴はなし）。

### セキュリティ (Security)
- defusedxml の導入により XML 関連攻撃に対する耐性を確保。
- RSS 取得に対して SSRF 防止（スキーム検証、プライベート IP 判定、リダイレクト検査）を実装。
- ネットワーク取得のサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェックでメモリ DoS を軽減。
- .env 読み込みで OS 環境変数を保護する protected オプションを導入（既存 env を意図せず上書きしない既定動作）。

### 既知の制限 / TODO
- pipeline.run_prices_etl の末尾実装がファイル内で途中（return の書式等）に見えるため、パイプラインの完全なエラーハンドリング・品質チェック連携は今後の整備が必要。
- strategy / execution パッケージはプレースホルダで、戦略実装と実売買連携は今後追加予定。
- テストカバレッジ・ユニットテストは明示的に同梱されていないため、モジュール毎にモックを用いたテスト整備が必要（ニュース取得の _urlopen は差し替え可能にしてある）。
- J-Quants API のレート制御は単一プロセス内の固定間隔スロットリング実装のため、マルチプロセスや分散環境では別途調整が必要。

### ドキュメント / 設計参照
- 各モジュールの docstring に設計方針や参照ドキュメント（DataPlatform.md, DataSchema.md 等）への言及が含まれています。実運用前に該当ドキュメントを参照してください。

---

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する際は運用上の追加情報や既知の変更点を反映してください。）