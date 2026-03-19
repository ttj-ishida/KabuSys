# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（version = 0.1.0）。主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数から設定値を取得する API を提供。
  - プロジェクトルート自動検出ロジックを実装（.git / pyproject.toml を探索）。
  - .env / .env.local の自動ロード機能（読み込み順序: OS 環境変数 > .env.local > .env）を実装。テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
  - .env の柔軟なパース処理:
    - コメント行、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - クォートなし値におけるインラインコメント判定。
  - 必須環境変数チェック用の _require()、環境値の検証（KABUSYS_ENV / LOG_LEVEL の妥当性チェック）を実装。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - 環境判定補助プロパティ（is_live / is_paper / is_dev）

- データ取得・永続化 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）と 429 の Retry-After 対応。
    - 401 を検出した場合はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB へ冪等的に保存する保存関数:
      - save_daily_quotes (raw_prices), save_financial_statements (raw_financials), save_market_calendar (market_calendar)
      - 各保存で fetched_at を UTC で記録、PK 欠損行スキップ、ON CONFLICT DO UPDATE による冪等性を確保。
    - 型変換ユーティリティ: _to_float / _to_int（不正値・空値は None、float 文字列の扱いなどに注意）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS からニュースを収集して raw_news / news_symbols に保存する一式を実装:
    - RSS フェッチ(fetch_rss) と前処理(preprocess_text)、記事 ID の生成(_make_article_id: 正規化 URL の SHA-256 先頭 32 文字)。
    - URL 正規化: トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去。
    - セキュリティ対策:
      - defusedxml を用いた XML パースで XML Bomb 等に対処。
      - SSRF 防止: _validate_url_scheme（http/https のみ）、リダイレクト検査用ハンドラ、ホストがプライベート/ループバック/リンクローカルでないことの検査。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - DB 保存:
      - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、新規挿入 ID を正確に返す。1 トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ一括保存（重複除去、チャンク挿入、RETURNING を利用）。
    - 銘柄コード抽出: テキストから 4 桁数字を抽出し、known_codes のフィルタを行う extract_stock_codes。
    - 統合ジョブ run_news_collection: 複数ソースを独立して処理し、失敗ソースはスキップ。新規挿入件数を返す。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用の DDL を追加（Raw レイヤー等のテーブル定義）:
    - raw_prices, raw_financials, raw_news, raw_executions（等、DataSchema.md に基づくテーブル群）。
  - 初期化・スキーマ管理の基礎を提供。

- 研究・特徴量 (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。レコード不足や定数分散をハンドリングして None を返す。
    - rank, factor_summary: ランキング（同順位は平均ランク）および基本統計（count/mean/std/min/max/median）を算出。
    - 設計方針: DuckDB の prices_daily のみ参照し、本番発注 API にはアクセスしない。標準ライブラリのみで実装。
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。必要行数が不足する場合は None。
    - calc_volatility: atr_20（20日 ATR）, atr_pct（相対 ATR）, avg_turnover（20日平均売買代金）, volume_ratio（当日出来高 / 20日平均）を計算。true_range 計算で NULL 伝播を制御し、部分窓の取り扱いに注意。
    - calc_value: raw_financials から直近財務（report_date <= target_date）を取得して PER (price / EPS), ROE を算出。EPS が 0/欠損の場合は None。
    - 定数（ウィンドウ長など）をモジュール内定義し、パフォーマンスのためスキャン範囲にバッファを取る実装。
  - research/__init__.py: 主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。data.stats.zscore_normalize を利用。

- 設計上の留意点（ドキュメント反映）
  - Research モジュールは DB のデータのみを参照し、外部発注やライブ口座へアクセスしない設計を明示。
  - Look-ahead bias 対策のため fetched_at の UTC 記録や、財務データは target_date 以前の最新レコードを使用する実装方針を反映。

### セキュリティ (Security)
- RSS パーサーで defusedxml を利用し、XML 関連攻撃を緩和。
- RSS フェッチ時の SSRF 対策:
  - URL スキーム検証（http/https のみ許可）。
  - リダイレクト先のスキーム・ホスト検査、プライベート IP 判定によるブロック。
- ネットワーク読込の最大バイト数制限（MAX_RESPONSE_BYTES）によるメモリ DoS / Gzip bomb 対策。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制限 / 注意事項
- calc_value の PBR・配当利回りは未実装（コメントに明記）。
- strategy / execution / monitoring パッケージは名前空間を用意していますが、実装は今バージョンでは限定的／未実装の箇所があります。
- .env パーサーは多くのケースに対応しますが極端に複雑なシンタックス（ネストした引用等）は想定外の挙動となる場合があります。
- J-Quants クライアントはネットワーク／API 側の挙動に依存するため、実運用ではログおよびレート制御の監視を推奨します。

### 開発者向け (Developer notes)
- 開発環境で自動 .env 読み込みを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB / SQLite のデフォルトパスは settings.duckdb_path / settings.sqlite_path で変更可能。

---
文書化されている設計方針・関数仕様はコード内ドキュメンテーション（docstring）に基づいて作成しました。必要であれば各モジュールごとの詳細な変更点や使用例を追記します。