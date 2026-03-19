# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

## [0.1.0] - 2026-03-19

初回公開リリース。以下の主要機能・実装を含みます。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ から親ディレクトリを探索して `.git` または `pyproject.toml` を基準に判定。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト向け）。
  - .env パーサは次の機能を持つ:
    - export プレフィックス対応、クォート（シングル/ダブル）のエスケープ処理、行内コメントの扱い（クォートなしの場合は空白直前の `#` をコメントとして扱う）などを考慮した堅牢なパース。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須変数チェック（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL のデフォルト、データベースパス（DUCKDB_PATH/SQLITE_PATH）のデフォルト値を提供。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）および LOG_LEVEL の妥当性チェック。
    - is_live / is_paper / is_dev のブールプロパティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔レートリミッタ（120 req/min）を導入（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
    - 401 Unauthorized 受信時はリフレッシュトークンを用いて ID トークンを自動更新して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）は pagination_key を利用して全件取得。
  - DuckDB への保存ユーティリティを追加（冪等保存）:
    - save_daily_quotes / save_financial_statements / save_market_calendar は INSERT ... ON CONFLICT DO UPDATE を用いる。
    - レコードの型変換ユーティリティ _to_float / _to_int を実装し、不正値を安全に None に変換。
    - fetched_at は UTC で記録し、取得時点をトレース可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と前処理の実装。
    - デフォルト RSS ソース（例: Yahoo Finance のカテゴリ RSS）を定義。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート）とそれに基づく記事ID生成（SHA-256 の先頭32文字）を実装し冪等性を保証。
    - XML パースに defusedxml を利用して XML Bomb 等の攻撃を防御。
    - SSRF 対策:
      - リダイレクト時にスキームとホストの事前検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）。
      - 接続前にホストのプライベート/ループバック/リンクローカル判定を行い内部アドレスへのアクセスを拒否。
      - 許可されるスキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - fetch_rss は幅広い RSS レイアウトに対するフォールバック処理（channel/item の有無など）を実装。
    - テキスト前処理（URL 除去・空白正規化）と pubDate パースの堅牢化（パース失敗時は warning ログで現在時刻にフォールバック）。
  - DuckDB 保存 API:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事IDを返す（チャンク処理、トランザクション管理あり）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをバルク挿入（ON CONFLICT で重複スキップ）し、挿入数を正確に返す。
    - run_news_collection: 複数 RSS ソースの統合収集ジョブ。各ソースは独立してエラーハンドリング（1 ソース失敗でも継続）。既知の銘柄コードセットを使った記事→銘柄紐付け処理を実装。
    - 銘柄コード抽出ユーティリティ extract_stock_codes を実装（4桁数字パターン、既知コードでフィルタ、重複除去）。

- リサーチ（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）にわたる将来リターンを DuckDB の prices_daily を参照して一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算。データ不足時（有効レコード < 3）は None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク扱い）と基本統計量（count/mean/std/min/max/median）計算を実装。丸めによる ties 検出漏れを防ぐため round(..., 12) を利用。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を prices_daily から計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（true range の単純平均）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range は high/low/prev_close のいずれかが NULL の場合は NULL として扱う（cnt_atr で判定）。
    - calc_value: raw_financials から target_date 以前の最新財務（EPS/ROE 等）を取得して PER/ROE を算出。EPS が 0/欠損 の場合は PER を None とする。
    - 主要関数はいずれも DuckDB 接続を引数に取り、prices_daily / raw_financials テーブルのみを参照する（外部 API にはアクセスしない設計）。
  - 研究用ユーティリティは kabusys.data.stats の zscore_normalize を再公開（__init__）。

- データスキーマ（kabusys.data.schema）
  - DuckDB スキーマ定義（DDL）を実装し、Raw / Processed / Feature / Execution の概念に基づくテーブル定義を用意（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を実装）。
  - 各テーブルに対する型チェック・制約（NOT NULL, CHECK, PRIMARY KEY 等）を定義。

### Security
- ニュース収集で SSRF 対策、レスポンス読み取りサイズ制限、defusedxml による XML パース保護を導入。
- J-Quants クライアントは認証トークンの管理と自動リフレッシュを実装し、不正なトークン状態からの回復を図る。

### Notes / 設計上の留意点
- research パッケージの関数は外部 API を呼ばず DuckDB 内のテーブルのみを参照するよう意図されており、バックテストや研究環境での安全な実行を狙いとしている。
- 多くの保存処理は冪等性（ON CONFLICT ..）を重視して実装されているため、再実行や差分取り込みに強い。
- 一部のモジュールはテストフックを持つ（例: news_collector._urlopen をモックして外部接続を差し替え可能）。

### Known limitations
- 現時点では Strategy / Execution / Monitoring の具象実装は未整備（パッケージ構造のプレースホルダあり）。
- factor_research の一部指標（PBR・配当利回り等）は未実装（factor_research 内で明示）。
- schema の実装はファイルにて部分的に定義（raw_executions の定義が途中で終わっているファイル断片が存在）。

---

今後のリリースでは下記のような点を予定・検討しています:
- Strategy および Execution レイヤの実装（発注ロジック・リスク管理・ポジション管理）。
- モニタリングと通知（Slack 連携の利用例・監視ジョブ）。
- schema の完全な初期化ユーティリティやマイグレーション機能の追加。