# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニング (https://semver.org/) を使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - pakage: kabusys の基本モジュール構成を追加（data, strategy, execution, monitoring を公開）。
  - バージョン情報を __version__ = "0.1.0" として設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）から .env, .env.local を読み込む。
    - OS 環境変数を保護する保護リスト機構（protected）を導入し、.env.local は .env を上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export KEY=val、クォート付き値、インラインコメント等のケースに対応。
  - 必須変数取得用の _require() と検証（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。
  - 設定の検証:
    - KABUSYS_ENV の許容値 (development, paper_trading, live) 検査。
    - LOG_LEVEL の許容値 (DEBUG, INFO, WARNING, ERROR, CRITICAL) 検査。
  - デフォルト DB パス (duckdb / sqlite) の既定値。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - API 呼び出し共通処理:
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
    - 401 受信時は自動的にリフレッシュして 1 回再試行（無限ループ防止）。
    - ページネーション用の pagination_key 管理（ページ間で id_token を共有するキャッシュ）。
  - データ保存関数（DuckDB）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存は冪等性を保つ（ON CONFLICT DO UPDATE）ようになっており、重複を上書きする設計。
    - fetched_at を UTC で記録し、いつデータが取得されたかをトレース可能に。
  - 型変換ユーティリティ（_to_float, _to_int）: 空文字や不正値に対する寛容な処理。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する処理を実装（DEFAULT_RSS_SOURCES に既定値）。
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカルでないことを確認（IP と DNS 解決を検査）。
      - リダイレクト時にも検証を行うカスタム HTTPRedirectHandler を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - Content-Length チェックと実際に読み込むバイト数の上限検査。
  - データ前処理:
    - URL 正規化 (_normalize_url): トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、クエリソート、フラグメント除去。
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で一意化（冪等性確保）。
    - テキスト前処理 (preprocess_text): URL 除去、空白正規化。
    - pubDate のパース（RFC 2822 → UTC naive datetime）、失敗時のフォールバック。
  - DB 保存:
    - save_raw_news はチャンク化して一括 INSERT を行い、INSERT ... RETURNING で実際に挿入された記事IDを返す。トランザクション内で処理。
    - save_news_symbols / _save_news_symbols_bulk によりニュースと銘柄の紐付けを効率的に保存（ON CONFLICT DO NOTHING、チャンク化、トランザクション）。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を抽出し、与えられた known_codes セットと照合して有効な銘柄コードだけを返す。

- スキーマ定義・初期化 (kabusys.data.schema)
  - DuckDB 用のデータベーススキーマを包括的に定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・チェック（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義（コード×日付、ステータス検索等）。
  - init_schema(db_path) で冪等にテーブルとインデックスを作成、get_connection() を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計とヘルパ関数を実装:
    - 差分更新のための最終日取得ヘルパ（get_last_price_date 等）。
    - 非営業日調整ロジック（_adjust_to_trading_day）。
    - run_prices_etl: 差分更新ルール（最終取得日の backfill を考慮して再取得）と J-Quants からの取得→保存処理のフローを実装（取得数・保存数を返す）。
  - ETLResult データクラス:
    - ETL 実行結果の集約（取得数、保存数、品質チェック結果、エラー一覧など）。
    - 品質チェックの重大度判定と辞書化メソッドを提供。
  - 設計方針に関する実装注釈:
    - デフォルトで backfill_days により後出し修正を吸収する挙動。
    - 品質チェックは Fail-Fast ではなく検出を集約して報告する方針。

### Security
- 上記ニュース収集モジュールにて SSRF 対策、XML パース保護、受信サイズ上限など複数のセキュリティ対策を実装。
- J-Quants クライアントは HTTP エラー処理・再試行を実装し、トークン流出などを防ぐための最小限の保護（Authorization ヘッダ伝播や再取得制御）を備える。

### Notes / Implementation details
- 多くの DB 操作は DuckDB を前提としており、INSERT ... ON CONFLICT / RETURNING を利用して冪等性と正確なカウントを担保する設計になっています。
- ネットワーク周りは urllib を利用して実装されており、テスト容易性のため一部（_urlopen や id_token 注入など）を差し替え可能な設計です。
- 設定周りはプロジェクトルート判定を __file__ ベースで行うため、CWD に依存しない挙動を意図しています。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

---

もし他に CHANGELOG に含めたい項目（リリース日付の変更、追加した機能の強調、既知の制約や今後の予定など）があれば教えてください。コードの追加差分やコミット履歴がある場合はそれに基づいてより正確な履歴を作成できます。