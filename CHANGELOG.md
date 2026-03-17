# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-17

### 追加
- パッケージ初期リリース。
- 基本パッケージ構成:
  - kabusys（トップパッケージ）を公開。__version__ = 0.1.0、__all__ に data, strategy, execution, monitoring を定義。
  - strategy / execution / monitoring パッケージのプレースホルダを追加（将来の拡張向け）。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。OS 環境変数の上書きを制御可能（.env.local が優先）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等で使用）。
  - .env パーサを実装：
    - export プレフィックス、シングル/ダブルクォート、クォート内のバックスラッシュエスケープ、行末コメントの扱い等に対応。
  - Settings クラスを提供し、環境変数をプロパティ形式で取得可能（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス等）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション機能を実装。
  - 必須変数取得時に未設定なら ValueError を投げる _require 関数を用意。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務(四半期 BS/PL)、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制限管理（120 req/min 固定間隔スロットリング）を実装（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx / ネットワークエラーに対応）。
  - 401 受信時は自動で id_token をリフレッシュして 1 回再試行する仕組みを実装（トークンのモジュールレベルキャッシュを保持）。
  - JSON デコード失敗時の詳細エラーメッセージ出力。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。fetched_at を UTC で記録し、冪等性を確保するため INSERT ... ON CONFLICT DO UPDATE を使用。
  - 値変換ユーティリティ _to_float / _to_int を実装（不正値や空値は None に変換。_to_int は "1.0" のような文字列を許容するが、小数部がある場合は None を返す等の安全策）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装。
  - セキュリティと堅牢性に配慮：
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクトハンドラでスキームとホスト/IP を検証、初回ホスト検証を実施。http/https 以外のスキーム拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip Bomb 対策）。
    - 受信時の Content-Length の事前チェック。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリソート）と、それに基づく記事ID生成（SHA-256 の先頭32文字）による冪等性。
  - テキスト前処理（URL 削除、空白正規化）。
  - INSERT ... RETURNING を用いたチャンク単位のバルク挿入（save_raw_news）で新規挿入された記事IDを返す実装。
  - news_symbols（記事と銘柄コードの紐付け）を一括で保存するメソッド（重複除去、チャンク挿入、RETURNING による実挿入数計測）。
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字のみ候補とし、known_codes によるフィルタ）。

- DuckDB スキーマと初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを定義して初期化する init_schema を実装。
  - 定義済みテーブル（Raw / Processed / Feature / Execution 層）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）およびパフォーマンス向けインデックスを定義。
  - init_schema は db ファイルの親ディレクトリを自動作成し、冪等的に DDL とインデックスを実行する。
  - get_connection により既存 DB への接続を提供。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass を導入し、ETL 実行結果（取得/保存件数、品質問題、エラー）を構造化して返却。
  - 差分更新ヘルパー（テーブルの最終取得日取得関数 get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 市場カレンダーを参照して非営業日を最寄り営業日に調整するヘルパー _adjust_to_trading_day を実装。
  - run_prices_etl を実装（差分更新ロジック：最終取得日から backfill_days 前を date_from として再取得。jquants_client の fetch/save を利用）。

### セキュリティ
- RSS 処理で defusedxml を使用して XML の脆弱性を緩和。
- ニュース収集で SSRF 対策（ホスト/IP のプライベート判定、リダイレクト検査、スキーム検証）を実装。
- 外部 HTTP 呼び出しでタイムアウトと最大受信バイト数を設定し、メモリ DoS を緩和。

### 内部（実装上の注記）
- jquants_client は API レート制限・リトライ・トークン自動リフレッシュ・ページネーションを考慮した堅牢な HTTP 呼び出しラッパを提供。
- news_collector は URL 正規化による記事重複回避と、記事ID のハッシュ化による冪等化を採用。
- DuckDB の保存処理は可能な限り冪等（ON CONFLICT 句）かつトランザクションでまとめている。
- pipeline モジュールは品質チェック（quality モジュール）との連携を想定した設計を持つ（品質問題は集約して ETLResult に格納）。

### 既知の問題 / 注意点
- run_prices_etl の戻り値についてソースコードの末尾が切れている（不完全な return 文の可能性）が確認される。実行時に想定する戻り値の整合性を確認・修正する必要があります（実装ミスの可能性）。
- strategy / execution / monitoring パッケージは現時点では実装がほとんどなく、将来の実装が必要です。
- 環境変数の自動読み込みはプロジェクトルート検出に依存するため、配布後や非標準レイアウトでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して手動管理することを推奨します。

## 参考
- 本リリースはコードベースの初回公開相当の内容を元に作成しています。実装の詳細・動作は実際の実行環境・テストにより確認してください。