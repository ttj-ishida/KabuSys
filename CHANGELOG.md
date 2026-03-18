CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]

0.1.0 - 2026-03-18
------------------

Added
- 初期リリース。パッケージバージョン = 0.1.0
- パッケージ公開
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring をトップレベル __all__ に定義

Config / 環境設定
- 環境変数管理モジュールを追加 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - .env 読み込みロジックはクォートやコメント、export プレフィックスに対応
  - .env.local は override=True で .env を上書き（ただし既に存在する OS 環境変数は保護）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスを提供（settings インスタンス）
    - 必須環境変数を _require 経由で検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）
    - LOG_LEVEL の許容値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

Data / J-Quants クライアント
- J-Quants API クライアントを追加 (kabusys.data.jquants_client)
  - API 呼び出しの基本機能 (_request)
    - ページネーション対応で複数ページ取得を行う fetch_* 関数
    - JSON デコードエラーハンドリング
    - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
    - リトライロジック: 最大3回、指数バックオフ。対象ステータス: 408, 429, 5xx（ネットワークエラーも再試行）
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）
    - モジュールレベルの id_token キャッシュ実装（ページネーション間で共有）
  - 認証: get_id_token(refresh_token=None) を提供（settings から refresh token を利用）
  - データ取得: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - クエリ引数（code, dateFrom, dateTo 等）をサポート
    - ページネーションキー処理により重複ループを回避
  - DuckDB への保存関数（冪等）
    - save_daily_quotes -> raw_prices へ ON CONFLICT DO UPDATE（PK: date, code）
    - save_financial_statements -> raw_financials へ ON CONFLICT DO UPDATE（PK: code, report_date, period_type）
    - save_market_calendar -> market_calendar へ ON CONFLICT DO UPDATE（PK: date）
    - 保存時に fetched_at を UTC ISO8601 で記録
  - 型変換ユーティリティを整備
    - _to_float: 空/不正値を None に変換
    - _to_int: "1.0" のような小数文字列は float 経由で変換し、小数部が存在する場合は None を返す

Data / ニュース収集
- RSS ニュース収集モジュールを追加 (kabusys.data.news_collector)
  - RSS フィード取得 (fetch_rss)
    - defusedxml による安全な XML パース（XML Bomb などに対応）
    - User-Agent / gzip 対応、Content-Length と読み取りバイト数上限（MAX_RESPONSE_BYTES = 10MB）で DoS 対策
    - gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - 最終 URL の再検証と SSRF 対策
      - リダイレクト前後でスキームとホストの検査を行う _SSRFBlockRedirectHandler / _urlopen を実装
      - _is_private_host によるプライベート/ループバック/リンクローカル判定（DNS 解決して A/AAAA をチェック）
      - http/https 以外のスキームは拒否
    - URL 正規化 (_normalize_url)：スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性）
    - コンテンツ前処理: URL 除去、空白正規化（preprocess_text）
    - pubDate のパースを補助する _parse_rss_datetime（パース失敗時は警告を出し現在時刻で代替）
    - デフォルト RSS ソース定義: Yahoo Finance のビジネスカテゴリ等
  - DB 保存
    - save_raw_news: チャンク分割（_INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのリストを返す。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクINSERT + ON CONFLICT DO NOTHING で保存。実挿入数を正確に返す。
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出し、known_codes と照合して重複除去して返す（正規表現で \b(\d{4})\b を使用）
  - 統合ジョブ: run_news_collection
    - 複数ソースごとに個別にエラーハンドリングし、1 ソース失敗でも他ソースは継続
    - 新規挿入記事に対して既知銘柄コードの紐付けを一括で行う
    - 返値: {source_name: 新規保存レコード数} の辞書

Data / スキーマ
- DuckDB スキーマ定義モジュールを追加 (kabusys.data.schema)
  - Raw Layer の DDL を定義
    - raw_prices: (date, code) を PK、数値に対する CHECK 制約を含む
    - raw_financials: (code, report_date, period_type) を PK、財務指標カラムを定義
    - raw_news: id を PK、datetime は NOT NULL
    - raw_executions: テーブル定義の一部が存在（発注/約定ログ用）
  - スキーマ定義は DataSchema.md に基づく設計思想を反映

Research / 特徴量・ファクタ計算
- 研究用モジュールを追加 (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離率）
      - 欠損やデータ不足時は None を返す
      - DuckDB のウィンドウ関数を活用して効率的に計算
    - calc_volatility(conn, target_date): atr_20（20日ATR 平均）, atr_pct, avg_turnover, volume_ratio
      - true_range を適切に NULL 伝播させ cnt_atr で十分なサンプルをチェック
    - calc_value(conn, target_date): per（株価/EPS）, roe（raw_financials から取得）
      - target_date 以前の最新財務データを銘柄ごとに取得して結合
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 各銘柄の将来リターンをまとめて 1 クエリで取得
      - horizons の検証（正の整数かつ <=252）
      - スキャン範囲を最長ホライズンの 2 倍カレンダー日で限定してパフォーマンス配慮
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算
      - None / 非有限値を除外し、有効レコードが 3 未満なら None を返す
      - 内部で rank ユーティリティを使用（同順位は平均ランク、round(..., 12) で float の丸め誤差対策）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算（None を除外）
  - すべての研究関数は DuckDB の prices_daily / raw_financials のみ参照し、本番発注 API へのアクセスは行わない設計
  - デフォルトで pandas 等の外部依存を使わず標準ライブラリ + duckdb で実装

Strategy / Execution / Monitoring
- strategy, execution, monitoring のパッケージプレースホルダを追加（__init__.py を含む）。実装はモジュール分割のための骨組み。

Logging / 設計方針
- ロギングを各モジュールで利用（logger = logging.getLogger(__name__)）
- Look-ahead bias 回避のため、外部データは fetched_at を UTC で記録
- API / DB 操作は冪等性を重視（ON CONFLICT / DO NOTHING / DO UPDATE を使用）
- 外部への副作用（発注や本番APIコール）は研究用関数から分離

Security / Safety
- RSS パーサーに defusedxml を使用
- ニュース取得時の SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクトの事前検証）
- HTTP レスポンスサイズ制限、gzip 解凍後のサイズ検査
- .env 読み込みのファイル読み込み例外は警告に変換して継続

Notes / 未実装・制限
- 一部テーブル定義（raw_executions など）はファイルの先頭で定義が続く想定（今回のコードは断片的）
- strategy / execution / monitoring の詳細な実装は別途追加予定
- zscore_normalize は kabusys.data.stats に依存しており、research パッケージの __init__ から再エクスポートしている（実体は別モジュール）

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Removed
- 初期リリースのため該当なし

Security
- RSS/HTTP の SSRF / DoS 対策を実装（詳細は上記）

以上。