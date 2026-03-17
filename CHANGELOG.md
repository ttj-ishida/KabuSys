CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトはまだ若いため、主に初期機能の追加が中心です。

Unreleased
----------

- 予定 / 開発中
  - テストカバレッジの拡充（単体テスト・統合テスト）
  - CLI / スケジューラ統合（ETLジョブの定期実行）
  - 監視・アラート（Slack 連携の詳細化）
  - 品質チェック（quality モジュールのルール追加と自動補正オプション）
  - ドキュメント整備（DataPlatform.md / API 使用例の追加）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ基盤
  - 初期パッケージ kabusys を追加。パッケージバージョンは 0.1.0。
  - モジュール分割: data, strategy, execution, monitoring を公開 API として定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して行い、CWD に依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env / .env.local の読み込み順と上書きルール（protected キーで OS 環境変数を保護）。
    - export KEY=val 形式、クォート付き値、インラインコメントの扱いに対応するパーサーを実装。
  - Settings クラスを追加し、主要設定をプロパティ経由で提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。
  - is_live / is_paper / is_dev のヘルパープロパティを提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得を実装。
  - レート制限対応: 固定間隔スロットリングに基づく RateLimiter（120 req/min）。
  - リトライロジック: 指数バックオフを使用した最大 3 回のリトライ（HTTP 408/429/5xx とネットワークエラーを対象）。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回再試行（無限再帰回避）。
  - id_token のモジュールレベルキャッシュを実装し、ページネーション間でトークン共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存と PK 欠損行スキップのログ出力を行う。
  - データ保存時に fetched_at を UTC ISO 形式で記録し、データが「いつ取得されたか」をトレース可能に。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集と raw_news テーブルへの保存フローを実装。
  - セキュリティ設計:
    - defusedxml を利用して XML Bomb 等を防御。
    - SSRF 対策: 非 http/https スキームやプライベート/ループバック/リンクローカル/マルチキャストアドレスへのアクセスを拒否（DNS 解決・IP 判定・リダイレクト検査含む）。
    - リダイレクト時もスキーム/ホストを検証するカスタム HTTPRedirectHandler を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）を設け、gzip 解凍後のサイズ検査（Gzip bomb 対策）を実装。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去し、クエリをキーでソート、フラグメント削除、小文字化を行う _normalize_url。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ先頭32文字で生成し、冪等性を担保。
  - テキスト前処理: URL 除去・空白正規化を行う preprocess_text。
  - RSS パース: content:encoded を優先、pubDate の RFC 2822 パースを実装（パース失敗時は代替時刻を使用）。
  - DuckDB 保存:
    - save_raw_news は INSERT ... RETURNING id を利用して実際に挿入された記事 ID を返却。チャンク分割とトランザクション管理を実装。
    - save_news_symbols / _save_news_symbols_bulk により article と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、RETURNING を利用して挿入数を正確に返す）。
  - 銘柄抽出: 正規表現による 4 桁コード抽出（\b(\d{4})\b）と known_codes によるフィルタリングを提供。
  - run_news_collection により複数 RSS ソースからの統合収集ジョブを実装。各ソースの失敗は他ソースに影響しない設計。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - 運用上頻出クエリ向けのインデックスを複数定義。
  - init_schema(db_path) によりファイルパス（または ":memory:"）で DuckDB を初期化し、テーブルとインデックスを作成するユーティリティを提供。get_connection で既存 DB への接続を取得可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL ワークフローの基礎を実装（差分更新、保存、品質チェックのフック）。
  - ETLResult データクラスを導入し、ETL の実行結果・品質問題・エラー概要を集約して返却可能に。
  - 差分更新補助:
    - テーブルの最終取得日を返すユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーに基づき非営業日から直近営業日に調整する _adjust_to_trading_day。
  - run_prices_etl を実装（差分計算・backfill の考慮・jquants_client 呼び出し・保存）。初期バックフィル日数はデフォルト 3 日。J-Quants データの開始日は 2017-01-01 として扱う。

Changed
- 新規リリースのための初期実装（多くの新機能追加）。設計ドキュメント（DataPlatform.md, DataSchema.md）に沿った構成を反映。

Security
- RSS 収集に関する複数のセキュリティ対策を導入（SSRF/リダイレクト検査、defusedxml、レスポンスサイズ制限、非 http(s) スキーム排除）。
- .env の自動読み込みはプロジェクトルート探索に基づくため、予期せぬ場所からの読み込みリスクを低減。

Fixed
- （初回リリース）該当なし（初期実装）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Notes / Implementation details
- いくつかの関数はテスト容易性を考慮して設計されています（例: news_collector._urlopen をモック可能）。
- DuckDB 保存は可能な限り冪等性を確保するため ON CONFLICT や RETURNING を活用しています。
- API リトライやトークンリフレッシュの挙動はログ出力で追跡可能にしてあり、運用時の調査を容易にしています。

ライセンス・貢献
- 貢献やバグ報告、改善提案は Issue / Pull Request を通じて受け付けてください。README に従って開発・テスト環境を準備してください。