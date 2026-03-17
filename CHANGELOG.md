Keep a Changelog に準拠した形式で、本コードベースから推測される変更履歴を日本語で作成しました。

CHANGELOG.md
============

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

バージョニングは semver に従います。

Unreleased
----------

- なし（今後の変更をここに記載）

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージの初期リリース: kabusys
  - パッケージ公開情報: src/kabusys/__init__.py （__version__ = "0.1.0"）
  - 基本モジュール群の骨組みを提供: data, strategy, execution, monitoring（strategy / execution / monitoring の一部はプレースホルダ）

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env 行パーサ実装（コメント行、export 形式、クォート内のエスケープ対応、インラインコメント処理）
  - Settings クラスを提供し、以下の設定プロパティを安全に取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live の検証)、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - ベースURL と API 呼び出しユーティリティを実装
  - レート制限: 固定間隔スロットリングで 120 req/min（_RateLimiter）
  - 再試行ロジック: 最大 3 回、指数バックオフ、408/429/5xx を対象
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（トークンキャッシュ共有）
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期財務データ)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への冪等保存 (ON CONFLICT DO UPDATE) 実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ保存時に fetched_at を UTC で記録し Look‑ahead bias を防止
  - 型安全な変換ユーティリティ: _to_float, _to_int

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と前処理、DuckDB への保存ワークフローを実装
    - fetch_rss: RSS の取得・XML パース（defusedxml 使用）、記事抽出、前処理
    - save_raw_news: chunked INSERT + RETURNING による新規挿入 ID 取得、トランザクションロジック
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes によるフィルタ）
    - run_news_collection: 複数ソースの統合収集ジョブ（ソース毎に独立してエラーハンドリング）
  - 設計上のポイント:
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
    - _normalize_url: トラッキングパラメータ除去（utm_* など）、クエリソート、フラグメント除去
    - preprocess_text: URL 除去、空白正規化
    - レスポンスサイズ保護 (MAX_RESPONSE_BYTES = 10MB)、gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - リダイレクト時にスキーム・ホストを検査するカスタム RedirectHandler
      - プライベート/ループバック/リンクローカルアドレスの拒否（直接 IP 解析 + DNS 解決）
    - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを含む

- スキーマ定義と初期化ユーティリティ (src/kabusys/data/schema.py)
  - DuckDB 用 DDL を包括的に定義（Raw / Processed / Feature / Execution 層）
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（典型的なクエリパターン向け）
  - init_schema(db_path) によりパスの親ディレクトリを自動作成してテーブル作成（冪等）
  - get_connection(db_path) による接続取得（スキーマ初期化は行わない）

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラス: 実行結果、品質問題、エラー一覧の集約
  - 差分更新ロジック設計:
    - 最小取得日 _MIN_DATA_DATE = 2017-01-01
    - デフォルト backfill_days = 3 による後出し修正の吸収
    - 市場カレンダー先読み _CALENDAR_LOOKAHEAD_DAYS = 90
  - ヘルパー:
    - _table_exists, _get_max_date
    - _adjust_to_trading_day: 非営業日の調整（market_calendar があれば過去方向に最も近い営業日に補正）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl 実装（差分取得 → 保存の流れ、ログ出力）
  - 品質チェックの呼び出し点を想定（quality モジュールとの連携設計）

Security
- XML パースに defusedxml を採用し XML Attack（XML bomb 等）への対策
- RSS/HTTP 周りで SSRF を意識した多段防御（スキーム検証、プライベートIP 判定、リダイレクト時検査）
- .env 読み込みで OS 環境変数を保護可能（protected set）および自動読み込みの無効化オプション

Logging / Observability
- 各モジュールで詳細な logger.info / warning / exception の出力を実装（取得件数、スキップ件数、再試行ログ等）
- ETLResult.to_dict により品質問題やエラーを構造化して監査ログに出力可能

Notable implementation details / 挙動
- J-Quants API コールはデフォルトでモジュールレベルの id_token キャッシュを利用し、ページネーション処理間で共有
- fetch_* 系は pagination_key を追跡して完全取得（重複キー検出でループ脱出）
- DuckDB への保存は INSERT ... ON CONFLICT で冪等化、news 保存は RETURNING を用いて実際に挿入された ID を取得
- 数値変換ユーティリティは不正値や小数誤変換を厳密に扱い、None を返すことで DB 側の NULL を使いやすくしている

Known issues / Limitations
- strategy/ execution / monitoring モジュールはパッケージには含まれているが実装は最小またはプレースホルダ（機能拡張が必要）
- pipeline.run_prices_etl の末尾がコード上で未完結（戻り値整形等の細部実装が残る可能性あり）
- quality モジュールは参照されているが、この抜粋に実装詳細は含まれていない（品質チェックの実体は別実装想定）
- デフォルト RSS ソースは限定的（必要に応じて sources 引数で拡張可能）

Upgrade notes
- 初回リリースのため既存利用者向けの互換性通知はなし。今後のリリースで breaking change がある場合は明示する予定。

Authors
- コードベースから推測される設計・実装者による初回リリース

----- 

（注）本 CHANGELOG は提示されたコードの内容から推測して作成しています。実際のコミット履歴や設計文書に基づいて必要に応じて日時・変更の粒度を修正してください。