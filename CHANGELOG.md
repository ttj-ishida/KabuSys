# Changelog

すべての重要なリリース変更履歴をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般:
- Semantic Versioning を採用しています。
- 主要な機能追加や破壊的変更は個別バージョンで記載します。

## [Unreleased]

### TODO / 今後の予定
- ETL パイプラインの細部（品質チェック結果の扱い・ログ出力強化）の追加実装。
- テストカバレッジ拡充（ネットワーク関連のモック、DuckDB 操作の統合テスト）。
- API クライアント・ニュース収集のメトリクス（取得レイテンシ、HTTP ステータス分布等）計測実装。
- run_prices_etl の戻り値に関する既知の不備の修正（0.1.0 リリース時点で未修正、詳細は下記 Known issues を参照）。

---

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システムの基盤となる主要モジュールを実装しました。

### 追加 (Added)
- パッケージのメタ情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring

- 設定管理 (kabusys.config)
  - .env / .env.local / OS 環境変数からの設定自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - 厳密な .env パース実装（コメント、export プレフィックス、クォート・エスケープ処理、インラインコメントルール）
  - Settings クラスを提供し、アプリケーションで使用する主要設定をプロパティとして公開
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス設定 (DUCKDB_PATH, SQLITE_PATH)
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証ロジック
    - is_live / is_paper / is_dev の利便性プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装
  - API レート制御（固定間隔スロットリング）: 120 req/min を遵守する _RateLimiter
  - 再試行ロジック: 指数バックオフ、最大リトライ回数、対象ステータス(408,429,5xx)
  - 401 (Unauthorized) 受信時の自動 ID トークンリフレッシュ（1 回のみリトライ）
  - id_token のモジュールレベルキャッシュ（ページネーション間でトークン共有）
  - JSON レスポンスのデコード検証
  - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar
    - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除
    - fetched_at に UTC タイムスタンプを記録し Look-ahead バイアス対策

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と raw_news への保存（DEFAULT_RSS_SOURCES に Yahoo Finance をデフォルト追加）
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への対策）
    - SSRF 対策: URL スキーム検証 (http/https のみ)、ホストがプライベート/ループバックでないか検査、リダイレクト検査用のカスタム RedirectHandler
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査
  - URL 正規化とトラッキングパラメータ削除（utm_*, fbclid, gclid 等）
  - 記事 ID 生成: 正規化 URL の SHA-256 の先頭32文字を使用（冪等性確保）
  - テキスト前処理（URL 除去、空白正規化）
  - DuckDB への一括挿入はチャンク化（_INSERT_CHUNK_SIZE）し、INSERT ... RETURNING で実際に挿入された行を返す
  - 銘柄抽出と紐付け:
    - 4桁数字パターンを用いた銘柄コード抽出（extract_stock_codes、known_codes を参照）
    - news_symbols への一括保存（ON CONFLICT DO NOTHING、RETURNING により挿入数を計測）

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw/Processed/Feature/Execution 層のテーブルを定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) でディレクトリ作成→全DDLとINDEXを実行し、初期化済みの DuckDB 接続を返す
  - get_connection(db_path) により既存 DB への接続を取得可能

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新のためのユーティリティ群を実装
    - 最終取得日の取得ヘルパー (get_last_price_date, get_last_financial_date, get_last_calendar_date)
    - 営業日に調整する _adjust_to_trading_day
  - run_prices_etl の骨組みを実装:
    - date_from 未指定時の最終取得日からの backfill ロジック（デフォルト backfill_days=3）
    - fetch_daily_quotes → save_daily_quotes を用いた差分取得と保存
  - ETL 実行結果を表す ETLResult dataclass（品質問題とエラー集約、辞書化用 to_dict）

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- なし（初期リリース）

### セキュリティ (Security)
- XML パースに defusedxml を使用して XML 関連の脆弱性を軽減
- ニュース収集での SSRF 対策を強化（スキーム検証、プライベートIP検出、リダイレクト時検査）
- 外部リソース取得時のレスポンスサイズ制限および gzip 解凍後の再チェックを導入し DoS 対策

### 性能 (Performance)
- API クライアントで固定間隔レート制御を導入し、レート制限超過による例外を防止
- ニュースのDB保存はチャンク化してトランザクションをまとめ、オーバーヘッドを削減

### 既知の問題 (Known issues)
- run_prices_etl の戻り値に不備がある可能性:
  - run_prices_etl の実装中、ファイル末尾で return 文が不完全（len(records), のみで saved を含めて返していない）になっています。ETL 呼び出し側で期待される (fetched_count, saved_count) のタプルが正しく返らないため、早急に修正が必要です。
- schema・ETL 実行時の型互換性やデータ型チェックは基本的にDDLにて制約を定義していますが、実運用では想定外の外部データにより INSERT エラーが発生する可能性があります。
- RSS フィードの多様なフォーマット（名前空間やカスタムレイアウト）に対する完全な網羅は行っていません。必要に応じてフィード毎のパーサ拡張が必要です。

### 依存関係（運用上の注意）
- 実行には次を想定:
  - Python 3.10+（型表記に union 型 | を利用）
  - duckdb
  - defusedxml
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- ローカルでの自動 .env ロードはプロジェクトルート検出に基づくため、パッケージ配布後に .env を自動で読み込む挙動は環境によって変わります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

メンテナンス / コントリビュート
- バグ報告や改善提案は issue を立ててください。特にネットワーク周りのリトライ挙動や RSS の互換性に関するフィードバックを歓迎します。