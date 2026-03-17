Keep a Changelog
================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)。
- 基本パッケージ構成
  - モジュール: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージバージョンを src/kabusys/__init__.py の __version__ にて "0.1.0" と定義。
- 環境設定管理
  - src/kabusys/config.py に Settings クラスを実装。環境変数から各種設定値（J-Quants トークン、kabuステーション API、Slack トークン/チャンネル、DBパス等）を取得。
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。OS 環境変数は .env によって上書きされないよう保護。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
  - 環境変数のパースは export 形式や引用符、インラインコメントの取り扱いに対応。
  - KABUSYS_ENV / LOG_LEVEL の値検証ロジックを実装（許可値チェック）。
- J-Quants データクライアント
  - src/kabusys/data/jquants_client.py を実装。
  - 機能: 日次株価（OHLCV）、四半期財務データ、マーケットカレンダー取得。
  - 実装上の特徴:
    - API レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
    - 401 受信時はリフレッシュトークンから id_token を再取得して 1 回だけ再試行。
    - ページネーション対応（pagination_key により複数ページ取得）。
    - 取得日時（fetched_at）を UTC で記録し、Look-ahead Bias の追跡を可能に。
    - DuckDB への保存は冪等性を保つ（INSERT ... ON CONFLICT DO UPDATE）。
    - 安全・堅牢な型変換ヘルパー（_to_float, _to_int）。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を実装。
  - 機能: RSS フィードからニュース記事を収集し raw_news に保存、記事と銘柄コードの紐付けを news_symbols に保存。
  - 実装上の特徴:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256（先頭32文字）による記事ID生成で冪等性を確保。
    - defusedxml を使用した XML パース（XML Bomb 等の対策）。
    - SSRF 対策:
      - リダイレクト先のスキーム/ホストを事前検証するカスタムハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであればアクセス拒否。
      - URL スキームは http/https のみ許可。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存はチャンク分割・トランザクション管理、INSERT ... RETURNING による実際に挿入された件数の取得。
    - 銘柄コード抽出（4桁数字パターン）を実装し既知コードセットでフィルタ。
- DuckDB スキーマ定義
  - src/kabusys/data/schema.py にスキーマ定義と初期化ロジックを実装。
  - レイヤ構造（Raw / Processed / Feature / Execution）に基づく多数のテーブル定義を提供:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と検索用インデックスを定義。
  - init_schema(db_path) によるディレクトリ自動作成と冪等なテーブル作成機能を提供。
- ETL パイプライン
  - src/kabusys/data/pipeline.py を実装（ETL の骨組み）。
  - 機能: 差分更新（最終取得日の算出、バックフィル日数の指定）、J-Quants からの取得→保存フローの実装方針を定義。
  - ETLResult データクラスによる実行結果集約（品質チェック結果、エラーの一覧を保持）。
  - 市場カレンダーに基づく営業日調整、テーブル存在チェック、テーブルごとの最終取得日時取得ヘルパー（get_last_price_date 等）を実装。
  - run_prices_etl の骨組み（差分算出、fetch_daily_quotes / save_daily_quotes 呼び出し）を実装。

Security
- 非公開情報の扱い・自動ロードでの保護:
  - OS 環境変数が .env により上書きされないよう保護セットを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを止められる。
- ニュース収集でのセキュリティ対策:
  - defusedxml による安全な XML パース。
  - SSRF（リダイレクト先含む）対策、プライベート IP の拒否、許可スキーム制限。
  - レスポンスサイズ制限（メモリ DoS 対策）、gzip 解凍後サイズ検証。

Known Issues / Notes
- run_prices_etl の戻り値実装
  - src/kabusys/data/pipeline.py 内の run_prices_etl 関数の末尾が現状不完全に見え（コード断片で "return len(records), " のように 2 番目の値が欠けている）、このままでは実行時エラーまたは未定義の挙動を引き起こす可能性があります。リリース前に戻り値の整備（取得件数と保存件数のタプルを正しく返す）を推奨します。
- その他の未実装/未完成箇所
  - strategy, execution, monitoring パッケージの __init__.py は存在するが、具体的な戦略ロジック・発注処理の実装は含まれていません（骨組みのみ）。
  - ETL の品質チェックモジュール（quality）参照はあるが、その実装はこのスナップショットに含まれていない可能性があります。品質チェック連携の実装状況に注意してください。

Compatibility
- Python 型アノテーションで | を利用しているため、Python 3.10 以降を想定。

Acknowledgements
- 初回リリース（ベース実装）として以下を含む堅牢化のための設計上の配慮を多数実装:
  - API レート制御、リトライ、トークン自動更新、冪等性、SSRF 防御、XML 安全化、DB トランザクション管理、レスポンスサイズ制限。

変更履歴の書式についてのお問い合わせや、特定モジュールの詳細な差分（例: テストケース、動作確認手順、将来の修正案）を希望される場合はお知らせください。