変更履歴 (Keep a Changelog 準拠)
================================

すべての変更はセマンティックバージョニングに従います。  
このファイルはパッケージ内のコードから推測して作成しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧 __all__ を定義。
- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は既存値を上書き）。
  - .env パーサーの実装（export プレフィックス、クォート、エスケープ、インラインコメントの扱いなどをサポート）。
  - Settings クラスにアプリケーション設定プロパティを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須化（未設定時は ValueError）。
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（development/paper_trading/live のみ許可）、LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw 層のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を含む）。
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した初期化向けDDLを提供。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - データ取得機能: 日足（prices/daily_quotes）、財務データ（fins/statements）、取引カレンダー（markets/trading_calendar）をページネーション対応で取得する関数を追加（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - 認証: refresh_token から id_token を取得する get_id_token を実装。
  - HTTP ユーティリティ:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。対象ステータス: 408 / 429 / 5xx。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰を回避）。
    - モジュールレベルの id_token キャッシュでページネーション呼び出し間の再利用を実現。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等（INSERT ... ON CONFLICT DO UPDATE）で保存。
    - 型変換ユーティリティ _to_float / _to_int を実装し、不正値を安全に None に変換。
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得と前処理機能を実装（fetch_rss, preprocess_text）。
    - defusedxml による安全な XML パースを使用（XML Bomb 等の対策）。
    - gzip 対応と受信バイト数上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策。
    - URL 正規化（トラッキングパラメータ除去・ソート・小文字化）と SHA-256 による記事ID生成（先頭32文字）。
    - SSRF 対策:
      - 初回ホスト検査でプライベートアドレスを拒否（_is_private_host）。
      - リダイレクト時にスキームとリダイレクト先のプライベートアドレスを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
      - http/https 以外のスキームを拒絶。
    - コンテンツの前処理（URL 削除、空白正規化）。
    - PubDate の安全なパース（RFC 2822 -> UTC naive）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を使い、実際に挿入された記事IDのリストを返す（チャンク & 単一トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING を使用）。
  - 銘柄コード抽出: テキストから 4 桁数字（\b\d{4}\b）を抽出し、既知コードセットでフィルタ（重複削除）。
  - 統合ジョブ run_news_collection を提供。ソースごとに独立エラーハンドリングし、known_codes を渡せば新規記事に対して銘柄紐付けを行う。
- Research（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト: 1,5,21 営業日）までの将来リターンを DuckDB の prices_daily 参照で一括計算。
    - calc_ic: factor_records と forward_records を code で結合して Spearman のランク相関（IC）を計算。十分な有効レコードがない場合は None を返す。
    - rank: 同順位は平均ランクを返すランク関数（浮動小数点丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 設計: DuckDB の prices_daily テーブルのみ参照、外部 API にアクセスしない、標準ライブラリのみで実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算（窓不足は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を正しく扱うロジックを実装。
    - calc_value: raw_financials の直近財務データと当日の株価を組み合わせて PER (EPS≠0 の場合) と ROE を算出。最新の財務レコードは report_date <= target_date の直近を選択。
  - research.__init__ で主要ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（kabusys.data.stats から））。
- 軽量設計方針
  - Research 系関数は本番口座や発注 API には一切アクセスせず、DuckDB のテーブル参照のみで完結することを明示。
  - 外部依存を最小化（feature_exploration は標準ライブラリのみで実装）。

Changed
- 初期リリースのため該当なし（初出）。

Fixed
- 初期リリースのため該当なし（初出）。

Security
- RSS 集約での SSRF 対策、defusedxml による XML パース、レスポンスサイズ上限、gzip 解凍後のサイズ検査など多数の安全策を導入。
- J-Quants クライアントでの認証リフレッシュ制御によりトークン漏れや無限再帰のリスクを軽減。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須。
- デフォルト値:
  - KABUSYS_ENV のデフォルトは "development"。有効値は development / paper_trading / live。
  - LOG_LEVEL のデフォルトは "INFO"。
  - KABU_API_BASE_URL のデフォルトは "http://localhost:18080/kabusapi"。
  - DUCKDB_PATH / SQLITE_PATH にデフォルトパスを使用。
- Research API は duckdb.DuckDBPyConnection を引数に取り、price/financial テーブルを参照するため、実行前に適切なテーブルとデータを用意してください。
- news_collector.fetch_rss は http/https スキーム以外の URL を拒否します。内部ホスト向け RSS を扱う際は注意してください。

Known limitations
- feature_exploration は pandas などの外部ライブラリ非依存で実装されているため、大規模データでのパフォーマンスは duckdb の SQL 側に依存します。
- schema の DDL はファイルの一部に留まっており、raw_executions の定義が途中で途切れている箇所があるため、完全なテーブル定義やマイグレーション処理は適宜補完が必要です（コードベースの抜粋に基づく注意）。

ライセンスや既知のサードパーティ依存
- 主な外部依存: duckdb, defusedxml（XML の安全パースに使用）。その他は標準ライブラリ中心で実装。

（以上）