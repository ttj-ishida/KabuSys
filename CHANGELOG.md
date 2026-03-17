# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/) の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリース記録です。

## Unreleased

（なし）

## [0.1.0] - 2026-03-17

初回公開リリース — KabuSys (日本株自動売買システム) の基本モジュール実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（`src/kabusys/__init__.py`）
    - __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring（モジュールの骨組みを準備）

- 環境設定 / 設定管理（`src/kabusys/config.py`）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動読み込み
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサを実装
    - export 区切りのサポート、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理
  - .env の読み込み時に OS 環境変数を保護する protected キーの仕組みを実装（override 引数で挙動制御）
  - 必須環境変数取得用の _require() と Settings クラスを実装
    - J-Quants / kabu API / Slack / データベースパス / 環境（development/paper_trading/live）/ログレベルの取得と検証
    - is_live / is_paper / is_dev の便利プロパティ

- J-Quants API クライアント（`src/kabusys/data/jquants_client.py`）
  - 基本的な HTTP 呼び出しラッパーと JSON レスポンス処理を実装
  - レート制限（120 req/min）を守る固定間隔 RateLimiter を実装
  - 再試行ロジック（指数バックオフ）を実装
    - 最大試行回数 3 回、リトライ対象ステータス(408, 429, 5xx)
    - 429 の場合は Retry-After ヘッダを考慮
  - 認証トークン取得 / キャッシュ / 自動リフレッシュを実装（401 時に1度だけトークンをリフレッシュしてリトライ）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE により重複更新を防止
  - データ整形ユーティリティ（_to_float, _to_int）により堅牢な型変換を提供
  - 取得時刻（fetched_at）を UTC で記録し、データの「いつ知り得たか」をトレース可能に

- ニュース収集モジュール（`src/kabusys/data/news_collector.py`）
  - RSS フィードから記事収集する機能を実装
    - デフォルト RSS ソース（Yahoo! Finance のカテゴリ RSS）を定義
    - RSS の取得・XML 解析・記事抽出（title, content, pubDate, link）を実装
  - セキュリティ・堅牢化
    - defusedxml を用いた XML パース（XML Bomb 等対策）
    - リダイレクト時のスキーム/ホスト検査による SSRF 防止（カスタムリダイレクトハンドラ）
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査
  - URL 正規化・トラッキングパラメータ除去（_normalize_url）と記事ID生成（SHA-256 の先頭32文字）
  - テキスト前処理（URL 除去・空白正規化）
  - DuckDB への保存（冪等）
    - save_raw_news は INSERT ... ON CONFLICT DO NOTHING と RETURNING を組み合わせ、実際に新規挿入された記事IDを返す（チャンク＆トランザクション）
    - save_news_symbols / _save_news_symbols_bulk で記事と銘柄（news_symbols）紐付けを一括挿入（重複排除、チャンク処理、トランザクション）
  - 銘柄コード抽出ロジック（4桁数字パターン）と既知銘柄セットフィルタ
  - 統合収集ジョブ run_news_collection を実装（ソース毎に独立したエラーハンドリング、symbols 紐付けを含む）

- DuckDB スキーマ定義・初期化（`src/kabusys/data/schema.py`）
  - DataPlatform に基づく 3 層＋実行レイヤーのテーブル定義を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約・PRIMARY KEY を定義（CHECK 制約含む）
  - 検索性向上のためのインデックスを定義（頻出パターンを想定）
  - init_schema(db_path) でスキーマを一括作成（親ディレクトリ自動生成対応）と get_connection API を提供

- ETL パイプライン基盤（`src/kabusys/data/pipeline.py`）
  - ETLResult データクラス（処理結果・品質問題・エラー情報を保持）を実装
  - スキーマ / テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）
  - 差分更新のための最終取得日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）
  - run_prices_etl の骨組みを実装
    - 差分取得ロジック（最後の取得日から backfill_days 分の前倒し再取得）
    - J-Quants クライアントを用いた取得と保存の連携（fetch_daily_quotes -> save_daily_quotes）
    - 取得範囲チェック・ログ出力

### セキュリティ (Security)
- RSS 処理における SSRF 対策を実装
  - リダイレクト先のスキーム検査・プライベートアドレス検査（_SSRFBlockRedirectHandler, _is_private_host）
  - URL スキーム制約（http/https のみ）
- XML パースに defusedxml を採用（外部エンティティやその他攻撃ベクトルの緩和）
- .env 読み込みで OS 環境変数を保護する機構を導入（protected set）

### パフォーマンス (Performance)
- J-Quants API のレート制御（固定スロット）と指数バックオフ再試行を実装
- NewsCollector の DB 挿入はチャンク分割（_INSERT_CHUNK_SIZE）および一括トランザクションで実行しオーバーヘッド削減
- raw -> processed など冪等性を持たせることで再実行・差分処理に適合

### 既知の問題 / 注意点 (Known issues / Notes)
- pipeline.run_prices_etl の戻り値の実装がファイル終端付近で中断しているように見え、現在のコード片では (len(records), ) のように不完全なタプルを返す可能性があります。呼び出し側は実装の完成を前提としないでください（要修正）。
- その他のジョブ（財務データ ETL、カレンダー ETL、品質チェック quality モジュールとの統合など）は設計骨子が揃っていますが、フルパイプラインの自動実行や監視・再試行戦略については追加実装が必要です。
- news_collector の DNS 解決で例外発生時は安全側（非プライベート）として扱う設計になっているため、特定環境では意図しないホストへアクセス許可が出る可能性がある点に注意してください（要運用ルール）。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

---

今後の追加候補（参考）
- run_prices_etl の戻り値とエラー集約の完成
- 財務データ / カレンダーの ETL 完成と品質チェック統合
- strategy / execution / monitoring の具象実装（現在はパッケージ骨組みのみ）
- 単体テスト・統合テスト、CI の追加（外部 API モック等）