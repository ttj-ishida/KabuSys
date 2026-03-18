# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
履歴は semver（MAJOR.MINOR.PATCH）に従います。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ全体
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - public サブパッケージ: data, strategy, execution, monitoring（現状は空パッケージの初期構成を含む）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.localの自動読み込み機能（プロジェクトルート検出は .git または pyproject.toml に基づく）
  - .env パースの堅牢化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数チェック用 _require と Settings クラスを提供
  - Settings で取得する主要キー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証ロジック
  - 環境に依存しないプロジェクトルート探索によりパッケージ配布後も機能

- データ取得クライアント: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しラッパー _request:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装
    - 再試行（指数バックオフ、最大 3 回）を実装（408/429/5xx を対象）
    - 401 受信時は ID トークンを自動リフレッシュして再試行（1 回まで）
    - ページネーション対応の fetch_* 関数群
    - JSON デコード／エラー処理の強化
  - 認証: get_id_token(refresh_token) を提供（settings からのトークン取得対応）
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - DuckDB への保存関数（冪等性を意識した実装）:
    - save_daily_quotes -> raw_prices テーブルに ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials テーブルに ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar テーブルに ON CONFLICT DO UPDATE
  - ユーティリティ: 安全な数値変換関数 _to_float / _to_int（不適切な値は None を返す）

- ニュース収集 (RSS) モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードの取得と記事保存処理を実装
  - セキュリティ/堅牢性機能:
    - defusedxml を使った XML パース（XML ボム等の防護）
    - SSRF 対策: リダイレクト時のスキーム検証と内部アドレス検出（_SSRFBlockRedirectHandler / _is_private_host）
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック
    - トラッキングパラメータ除去（utm_* 等）による URL 正規化と記事ID生成（SHA-256 の先頭32文字）
  - RSS パースと記事前処理:
    - URL 除去、空白正規化を行う preprocess_text
    - pubDate のパースと UTC 変換（失敗時は警告ログで現在時刻に代替）
  - DB 保存（DuckDB）:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用。トランザクション処理・ロールバック対応
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク化して保存。INSERT RETURNING による実挿入数の取得
  - 銘柄コード抽出: テキストから 4 桁の数値を抽出し、 known_codes セットでフィルタする extract_stock_codes
  - 統合ジョブ run_news_collection: 複数ソースを個別に処理し、既知銘柄と紐付けを行う

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw レイヤー用テーブル定義（raw_prices, raw_financials, raw_news, raw_executions の DDL を含む（partial））
  - テーブル定義は DataSchema.md に基づく設計方針を反映（Raw/Processed/Feature/Execution 層の想定）
  - DDL における制約（主キー、型チェック、NOT NULL、DEFAULT 等）を定義

- リサーチ用モジュール (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None)
      - prices_daily テーブルから将来リターン（デフォルト [1,5,21]）を一括クエリで計算
      - horizons のバリデーション（正の整数かつ <= 252）
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - ファクターと将来リターンを code で結合して Spearman の ρ（ランク相関）を計算（有効レコード < 3 の場合は None）
      - 内部に rank ユーティリティを実装（同順位は平均ランク、round による ties 対策）
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を計算（None や非有限値を除外）
  - factor_research.py:
    - calc_momentum(conn, target_date)
      - mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を prices_daily から計算
      - スキャン範囲のバッファを考慮（営業日→カレンダー日換算のバッファ）
    - calc_volatility(conn, target_date)
      - atr_20（20日 ATR の単純平均）、atr_pct、avg_turnover、volume_ratio を計算
      - true_range の NULL 伝播制御、cnt_atr によるデータ不足判定
    - calc_value(conn, target_date)
      - raw_financials から最新財務情報を結合し PER（EPS 0/欠損時は None）、ROE を計算
  - research パッケージ __init__ で各関数を再エクスポート（zscore_normalize は kabusys.data.stats から取り込み）

### Changed
- 初版のため該当なし（新規追加のみ）

### Fixed
- 初版のため該当なし

### Security
- ニュース収集で SSRF 対策、XML インジェクション対策、レスポンスサイズ制限、URL スキーム検証などのセキュリティ設計を盛り込んでいることを明記

## 既知の注意点・運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらは Settings により _require() で未設定時に ValueError を送出します
- DuckDB / defusedxml の依存:
  - モジュールは duckdb と defusedxml に依存します。環境にインストールしてお使いください。
- DB 初期化:
  - schema モジュールの DDL を実行して必要なテーブルを作成してください（raw_prices, raw_financials, raw_news, market_calendar 等）
- Look-ahead bias 注意:
  - J-Quants クライアントは fetched_at を UTC で記録し、いつデータを取得したかを追跡できるように設計されています。研究・バックテストでの扱いに注意してください
- 本番発注系について:
  - strategy / execution / monitoring パッケージはインターフェース準備済み（初期化）。本リリースのデータ/リサーチ機能は本番の発注 API へは接続しない前提で設計されています

## 将来検討事項
- processed / feature レイヤーの自動生成スクリプト（prices_daily 等の ETL）
- strategy / execution の具体的な発注実装（kabuステーション連携）
- より高度なファクター（PBR、配当利回り等）の追加
- 単体テストおよび統合テストの追加（ネットワーク依存部分のモック化）

----

参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/