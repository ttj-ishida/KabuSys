# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

現在のリリース履歴:

## [0.1.0] - 2026-03-18
初回公開。日本株自動売買システム「KabuSys」の基本機能群を実装しました。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化。バージョン: 0.1.0。
  - パッケージ公開用の __all__ 定義 (data, strategy, execution, monitoring)。

- 設定管理 (kabusys.config)
  - .env/.env.local または環境変数から設定をロードする自動読み込み機能を実装。プロジェクトルート判定は .git / pyproject.toml を基準に行う（CWD 非依存）。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、環境変数からの取得・バリデーションを行うプロパティ群を実装。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）やログレベル（LOG_LEVEL）、環境（KABUSYS_ENV: development|paper_trading|live）に対する既定値と検証。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
    - リトライ戦略: 指数バックオフ、最大3回、408/429/5xx をリトライ対象に。429 の Retry-After を考慮。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して再試行（無限再帰防止）。
    - id_token のモジュールレベルキャッシュを提供（ページネーション間で共有）。
    - JSON レスポンスのデコードやエラーハンドリングを実装。
  - API 用のユーティリティ関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes (raw_prices)、save_financial_statements (raw_financials)、save_market_calendar (market_calendar)。
    - ON CONFLICT DO UPDATE を用いた冪等挿入、fetched_at の記録、PK 欠損行のスキップとログ出力。
  - 型変換ユーティリティ: _to_float, _to_int（文字列 → 数値の堅牢な変換ロジック）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集と前処理の実装:
    - fetch_rss：RSS 取得・パース（defusedxml を使用）、content:encoded の優先使用、タイトル/本文の前処理（URL除去、空白正規化）、pubDate のパース。
    - URL 正規化 (tracking パラメータ除去、スキーム/ホスト小文字化、フラグメント削除) と記事ID生成（normalized URL の SHA-256 の先頭32文字）。
    - SSRF 対策:
      - 取得前のホストプライベート判定、リダイレクト時の検査用ハンドラ（_SSRFBlockRedirectHandler）実装。
      - 許可スキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍時の検査（Gzip bomb 対策）。
    - XML パース失敗や不正レスポンス時は安全にスキップし警告ログを出力。
  - DB 保存機能:
    - save_raw_news：チャンク挿入＋INSERT ... RETURNING id を用い、新規挿入された記事IDのみを返す。トランザクションでまとめて処理、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk：news_symbols テーブルへの銘柄紐付けをチャンク挿入で行い、挿入数を正確に返す。ON CONFLICT で重複スキップ。
  - 銘柄コード抽出:
    - extract_stock_codes：テキストから 4 桁のコードを抽出し、既知コードセットでフィルタ。重複除去して返す。
  - 統合ジョブ run_news_collection：複数 RSS ソースから収集→保存→銘柄紐付け を実行。ソース単位でエラーハンドリングを行い、1 ソース失敗でも他は継続。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用 DDL を定義するモジュールを追加（Raw / Processed / Feature / Execution 層設計に基づく）。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（CHECK 制約、PRIMARY KEY 等）を含むDDL文字列を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns：DuckDB の prices_daily を参照して将来リターンを一度のクエリでまとめて取得。ホライズン指定、データ不足時は None。
    - calc_ic：ファクター値と将来リターンの Spearman ランク相関（IC）を計算。ties の処理や最小レコード数チェックを実装。
    - rank：同順位を平均ランクにするランク関数（round(v, 12) による丸めで浮動小数誤差を緩和）。
    - factor_summary：ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
  - factor_research モジュール:
    - calc_momentum：mom_1m, mom_3m, mom_6m, ma200_dev を prices_daily から計算。ウィンドウ不足時は None。
    - calc_volatility：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。true_range 計算時の NULL 伝播制御に注意。
    - calc_value：raw_financials から target_date 以前の最新財務を取得して PER（close / eps）と ROE を計算。EPS が 0/欠損のときは None。
  - 研究モジュール __init__ で代表的関数を公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）および zscore_normalize（kabusys.data.stats からのユーティリティ参照）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### セキュリティ
- news_collector にて以下のセキュリティ対策を実装:
  - defusedxml を利用した XML パース（XML Bomb 等の防御）。
  - SSRF 対策: リダイレクト検査、プライベートIP/ループバック/リンクローカル判定、スキーム検証。
  - レスポンスサイズ制限と Gzip 解凍後サイズ検査（DoS 対策）。
  - URL スキーム検証や不正な link のスキップ。
- J-Quants クライアントは認証トークン扱いで自動リフレッシュを行い、無限再帰しない設計を採用。

### 既知の注意点 / 移行メモ
- 必須環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）が未設定だと Settings のプロパティアクセス時に ValueError を送出します。初期設定時は .env/.env.local を用意してください。
- 自動 .env 読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ定義の続き（Execution 層など）や data.stats の具体実装は本バージョンで参照はあるものの、別モジュールでの実装が必要です（存在しない場合、インポートエラーが発生する可能性があります）。
- news_collector の extract_stock_codes は単純な正規表現（4桁）ベースのため、誤抽出の可能性がある点に注意してください（known_codes を渡すことで精度向上）。

もし CHANGELOG に追加してほしい詳細（例えば各関数の例や CLI / データベース初期化手順など）があれば教えてください。必要に応じて項目を分割してより細かく記載します。