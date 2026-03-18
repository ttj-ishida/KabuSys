# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（初期リリース相当）の内容から推測して作成しています。

全般的な注記
- バージョンはパッケージ内定義 __version__ = "0.1.0" に合わせています。
- 日付は本ファイル作成日（2026-03-18）を使用しています。実際のリリース日が異なる場合は適宜更新してください。

Unreleased
- なし

[0.1.0] - 2026-03-18
Added
- パッケージ初期構成
  - kabusys パッケージの基盤を追加。サブパッケージとして data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
  - .env の行パーサを実装（export プレフィックス対応、クォート内エスケープ、行内コメント処理など）。
  - Settings クラスを導入し、型付きプロパティ経由で設定値を取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須値の検証（未設定時は ValueError）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値を設定。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証ロジック。
    - is_live / is_paper / is_dev のヘルパープロパティ。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API クライアント実装（株価日足、財務データ、マーケットカレンダーの取得機能）。
  - レート制限制御（固定間隔スロットリング）で 120 req/min を遵守する実装（内部 RateLimiter）。
  - リトライロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時はリフレッシュトークンを用いて自動で ID トークンを更新し 1 回リトライする仕組みを追加。
  - ページネーション対応の fetch 関数（fetch_daily_quotes, fetch_financial_statements）を実装。pagination_key による繰り返し取得をサポート。
  - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除／更新。
  - データ変換ユーティリティ _to_float / _to_int を追加（安全な数値変換、空値や不正値の扱いを統一）。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead バイアスに対するトレーサビリティを確保。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する ETL 機能を実装。
  - セキュリティ対策・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: 最初の URL 検証と、リダイレクト時にスキーム/ホスト検査を行うカスタム HTTPRedirectHandler を実装。
    - 非 http/https スキーム拒否、プライベート IP（ループバック/リンクローカル等）へのアクセス拒否。
    - レスポンスの最大読み取りサイズ（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）、SHA-256（先頭32文字）で記事 ID を生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - RSS の柔軟なパース: content:encoded を優先、channel/item 要素がない場合のフォールバック検出を実装。
  - DuckDB へバルク挿入（チャンク分割）とトランザクション処理を実装。INSERT ... RETURNING を用い、実際に挿入された記事IDリストや挿入件数を正確に返す。
  - 銘柄コード抽出ロジック（4桁数字）と、既知の銘柄セット known_codes によるフィルタリングを実装。重複排除。
  - run_news_collection を実装し、複数 RSS ソースの収集・保存・銘柄紐付けを統合的に実行（各ソースは独立してエラーハンドリング）。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema に基づく包括的なスキーマを追加。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型・制約（CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
  - 利用頻度を想定したインデックスを定義。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、:memory: 対応）。
  - get_connection(db_path) で既存 DB へ接続可能。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を追加し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を構造化して返却する仕組みを導入。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得）を実装。
  - 市場カレンダーに基づき、非営業日の場合に直近営業日に調整する _adjust_to_trading_day を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装して差分更新に利用。
  - run_prices_etl を実装（差分取得のロジック、backfill_days による過去再取得、J-Quants クライアント経由での取得と保存）。
- その他
  - news_collector と jquants_client はテスト容易性を考慮して、HTTP 呼び出し部分を差し替え（_urlopen 等）可能に設計。

Security
- defusedxml による安全な XML パースを採用（XML ベース攻撃の緩和）。
- RSS 収集での SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト時の検査）。
- レスポンスボディサイズ制限と gzip 解凍後の再チェック（メモリ DoS / Gzip bomb の緩和）。
- .env 読み込みで OS 環境変数を保護する protected 機構（既存の OS 環境変数を上書きしない既定動作）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Notes / Known issues / TODO（コードから推測）
- pipeline.run_prices_etl の実装は差分更新と backfill を意図しており、他の ETL ジョブ（financials, calendar）も同様の差分ロジックを採用する想定。品質チェック（quality モジュール）との統合が予定されているが、本コードベースでは quality モジュール参照のみで詳細は未提示。
- strategy/execution/monitoring パッケージはエントリのみ（__init__.py が空）で、個別戦略や発注ロジックは今後実装予定。
- 実運用においては J-Quants のリクエスト制限や Slack 等通知の運用設計、DuckDB ファイルのバックアップ・ローテーション、マルチプロセスからの同時アクセスなどの運用面要件を追加検討する必要あり。

参考: 主要ファイル一覧
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py

もしこの CHANGELOG をリリースノート用に整備する・日付やカテゴリを調整する必要があれば、実際のコミット履歴やリリースポリシーに合わせて更新します。どの程度の詳細（関数レベルの変更ログや開発者向けの技術ノート）を追加するか指示ください。