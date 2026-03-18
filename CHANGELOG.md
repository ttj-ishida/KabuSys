# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
慣例: 変更は安定したリリース単位で記載します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買・データ基盤のコア機能を実装しています。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージのバージョン定義 (__version__ = "0.1.0") と公開サブパッケージ指定（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない読み込みが可能。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パース機能（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスを導入し、アプリ固有の設定プロパティを提供:
      - J-Quants / kabuステーション / Slack の必須トークン取得メソッド（未設定時は ValueError）。
      - データベースパスの既定値（DuckDB/SQLite）。
      - 環境（development/paper_trading/live）のバリデーションとログレベルの検証。
      - ユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants データ取得クライアント
  - src/kabusys/data/jquants_client.py
    - API レート制御（120 req/min）を行う固定間隔スロットリング実装（_RateLimiter）。
    - トークンキャッシュと自動リフレッシュ（get_id_token / _get_cached_token）。
    - HTTP リクエストラッパー（_request）にリトライ（指数バックオフ）、429 の Retry-After 対応、401 の一度の自動リフレッシュを実装。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - データ変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に扱う。

- ニュース収集 / RSS パイプライン
  - src/kabusys/data/news_collector.py
    - RSS フィード取得（fetch_rss）と記事抽出ロジックを実装。
      - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
      - gzip 圧縮対応と受信サイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）。
      - SSRF 対策: リダイレクト時のスキーム検証とプライベートアドレス検査（_SSRFBlockRedirectHandler、_is_private_host）。
      - URL 正規化とトラッキングパラメータ除去 (_normalize_url)。
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成 (_make_article_id)。
      - テキスト前処理（URL 除去、空白正規化）。
      - RSS pubDate のパース（_parse_rss_datetime）。
    - DuckDB への保存処理:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク毎に実行し、INSERT RETURNING で実際に挿入された記事IDを返す。トランザクション管理あり。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括で保存、INSERT RETURNING による実挿入数検出。チャンク & トランザクション処理。
    - 銘柄抽出ロジック:
      - extract_stock_codes: テキストから4桁銘柄コードを抽出し、既知銘柄セットでフィルタ。重複除去。
    - 全体ワークフロー:
      - run_news_collection: 複数 RSS ソースを独立に処理し、エラーがあっても他ソースは継続。既知銘柄が与えられた場合は新規記事に対して銘柄紐付けを実行。

- 研究用ファクター（Research）モジュール
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（DuckDB の prices_daily を参照）。
      - 複数ホライズンを一度に取得する SQL 実装、ホライズンに対する入力検証（正の整数、252 以下）。
      - 結果は date, code と各ホライズンの fwd_{n}d を含む dict のリストとして返す。
    - IC（Information Coefficient）計算 calc_ic（Spearman の rho に相当するランク相関）。
      - None / 非有限値の除外、データ不足時（<3）には None を返す。
      - ランク変換は同順位を平均ランクとする rank ユーティリティを使用（丸め誤差対策あり）。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算。
    - 実装は pandas 等に依存せず標準ライブラリ + duckdb を前提。

  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、および 200日移動平均乖離 ma200_dev（必要行数が足りない場合は None）。
      - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、当日出来高比率（volume_ratio）。
      - calc_value: raw_financials から直近の財務を取得し、PER/EPS、ROE を計算（EPS=0/欠損時は None）。
    - DuckDB のウィンドウ関数や LAG/AVG/COUNT を使用した SQL 実装。価格・財務テーブルのみ参照する設計。

  - src/kabusys/research/__init__.py
    - 主要関数をパッケージ公開: calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）、calc_forward_returns, calc_ic, factor_summary, rank。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py
    - Raw Layer のテーブル DDL を追加:
      - raw_prices, raw_financials, raw_news, raw_executions（raw_executions の DDL はファイル内に定義開始あり、以降の実装を拡張可能）
    - スキーマ管理と初期化の土台を実装（DDL 定義をコード化）。

- その他
  - src/kabusys/data パッケージ内でデータ取得・保存・前処理に関する複数ユーティリティを整備（J-Quants クライアント、ニュースコレクター、スキーマ）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- RSS / HTTP 周りの堅牢化:
  - defusedxml の導入による XML パースの安全化。
  - SSRF 対策: リダイレクト先のスキーム検査・プライベートアドレス検出、初期 URL のホスト検査。
  - レスポンスサイズ制限と gzip 解凍後の再チェック（Gzip Bomb 対策）。
- 環境変数読み込みの保護:
  - OS 環境変数の保護（自動ロード時に既存環境変数は上書きされないよう動作）。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 既知の制限 / 注意点 (Known Issues / Notes)
- data.stats の zscore_normalize は research パッケージで import しているが、本リリースに含まれるかはコードベース全体の配置に依存します（別モジュールとして提供される想定）。
- raw_executions テーブルの DDL の続きや Execution / Monitoring / Strategy パッケージの実装は本リリースでは最小限（雛形）であり、今後の実装で拡張予定。
- J-Quants クライアントはネットワーク・API 例外を呼び出し元へ伝播します。運用時は適切な例外ハンドリングを行ってください。

---

今後のリリースでは、Execution（発注・ポジション管理）、Strategy（戦略実装）、Monitoring（監視／アラート）などの機能拡張、スキーマの完成、テストカバレッジの拡充を予定しています。