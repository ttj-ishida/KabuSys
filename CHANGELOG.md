# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初版リリースを記録しています。

全般:
- バージョニングは package の __version__ に従います（0.1.0）。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ基盤
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開。strategy/execution パッケージは現時点では初期プレースホルダ（空）として用意。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートを .git または pyproject.toml で検出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサー実装:
    - コメント行、先頭の `export `、クォートされた値のエスケープ処理、インラインコメント処理などに対応。
    - override/protected オプションにより OS 環境変数を保護しつつ .env.local で上書き可能。
  - セッティングプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として明示的に読み出す _require() を実装。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等にデフォルトを提供。
    - KABUSYS_ENV（development, paper_trading, live）および LOG_LEVEL（DEBUG..CRITICAL）のバリデーションを追加。
    - is_live/is_paper/is_dev のユーティリティプロパティを提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - データ取得機能を実装（株価日足、財務諸表、マーケットカレンダー）。
  - 設計上の特徴:
    - API レート制限 (120 req/min) を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、ステータス 408/429/5xx に対応）。
    - 401 受信時には自動で ID トークンをリフレッシュして 1 回だけ再試行。
    - ページネーション対応（pagination_key を用いた連続取得）。
    - モジュールレベルの ID トークンキャッシュを持ち、ページネーション間で共有。
    - JSON デコード失敗時にわかりやすい例外を投げる。
  - DuckDB への保存 API:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 挿入は冪等に（ON CONFLICT DO UPDATE）実装し、PK 欠損行はスキップしてログ警告。
    - 型変換ユーティリティ _to_float, _to_int を追加（安全な数値変換、"1.0" 等の取り扱いを考慮）。
  - ロギングで取得件数・保存件数を記録。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し DuckDB の raw_news, news_symbols に保存する機能を実装。
  - 設計上の特徴（セキュリティ／堅牢性重視）:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストのプライベート/ループバック/リンクローカル判定（IP 直接判定 + DNS 解決によるチェック）。
      - リダイレクト時にスキーム/ホストを検査するカスタム RedirectHandler を導入。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設け、Gzip 解凍後もサイズチェック（Gzip Bomb 対策）。
    - トラッキングパラメータ（utm_*, fbclid 等）の除去と URL 正規化処理。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - テキスト前処理（URL 削除、空白正規化）。
    - raw_news へのバルク挿入はチャンク化してトランザクションで行い、INSERT ... RETURNING を使って実際に挿入された ID を取得。
    - news_symbols（記事⇔銘柄紐付け）の一括挿入ユーティリティ（重複除去・チャンク処理・トランザクション管理）。
  - 銘柄抽出: 正規表現で 4 桁数字を抽出し、既知の銘柄セットでフィルタする extract_stock_codes 実装。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを追加。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく多層スキーマを定義:
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PK, CHECK, FOREIGN KEY）を定義。
  - 頻出クエリ用のインデックスを複数定義。
  - init_schema(db_path) でディレクトリ作成（必要時）→ 接続 → DDL 実行 → インデックス作成までまとめて行うユーティリティを提供。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を導入し、ETL の実行結果（取得数・保存数・品質問題・エラー群）を構造化。
  - スキーマ存在チェック、テーブル最大日付取得ユーティリティを提供（差分更新に利用）。
  - market_calendar を参照して非営業日を過去方向に調整するヘルパー _adjust_to_trading_day。
  - 差分更新方針:
    - 最終取得日ベースの差分取得（バックフィル日数により数日前から再取得して API の後出し修正を吸収）。
    - run_prices_etl の基本骨格を実装（date_from 自動算出、fetch → save を呼び出す流れ）。
  - 品質チェックモジュール（quality）との連携を想定した設計（品質問題は集めて ETLResult に格納）。

Changed
- 新規パッケージのため該当なし。

Fixed
- 新規パッケージのため該当なし。

Security
- RSS 処理周りで複数の安全対策を導入:
  - defusedxml による安全な XML パース
  - SSRF 対策（スキーム検証、プライベートアドレス検査、リダイレクト検査）
  - レスポンスサイズ上限、gzip 解凍後サイズ検査（DoS / Bomb 対策）
- .env の読み込みで OS 環境変数を保護する protected オプションを導入（.env.local 等で不用意な上書きを防止）。

Notes / Known limitations
- strategy/execution モジュールは現在プレースホルダ（空パッケージ）。実際の戦略ロジックや発注処理は今後の実装予定。
- pipeline.run_prices_etl は差分取得の骨格を実装していますが、他の ETL ジョブ（財務・カレンダー等）の統合ワークフローや品質チェックとの完全な統合は今後の拡張対象。
- DuckDB への接続 API は同期（blocking）実装。大規模並列フェッチなどの最適化は将来検討。

Upgrade Notes
- 0.1.0 は初回リリースのため、移行・破壊的変更はありません。

Contributors
- コードベース記述に基づき自動生成した CHANGELOG（実装者はソースコードの作成者を参照してください）。