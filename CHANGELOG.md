# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
重大度はセマンティックバージョニングに従います。

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-03-18

初回リリース — 日本株自動売買システム「KabuSys」のコア実装を追加しました。  
本リリースではデータ収集・スキーマ定義・特徴量算出・環境設定・ニュース収集・外部 API クライアントの基盤機能を実装しています。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys/__init__.py）。バージョン: 0.1.0。
  - パッケージが公開するサブパッケージ: data, strategy, execution, monitoring。

- 環境設定 / .env 自動読み込み（kabusys.config）
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を基準）。作業ディレクトリに依存せずに .env を読み込めます。
  - .env パーサを実装: コメント行、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
  - .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ユーティリティ _require と Settings クラスを追加。主な設定:
    - JQUANTS_REFRESH_TOKEN（J-Quants 用）
    - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack）
    - DUCKDB_PATH, SQLITE_PATH（データベースパス）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
  - Settings に is_live / is_paper / is_dev などのユーティリティプロパティを追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ _request を実装（JSON デコード検証、タイムアウト、パラメータ付与）。
  - レート制限の実装: 固定間隔スロットリング（120 req/min）。_RateLimiter。
  - 再試行ロジック: 指数バックオフ（最大3回）、特定ステータス（408, 429, 5xx）でリトライ、429 の Retry-After を優先。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）を実装。id_token のモジュールレベルキャッシュを保持。
  - ページネーション対応でデータを取得する fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes → raw_prices テーブルに保存（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials テーブルに保存（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar テーブルに保存（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ _to_float / _to_int を追加（無効値は None、"1.0" のような表現の扱いを考慮）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードを安全に取得・解析する実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL/リダイレクト先のスキーム検査（http/https のみ）、プライベート IP/ループバック/リンクローカルの検査（DNS 解決した A/AAAA レコードをチェック）。
    - リダイレクト時にも検査する専用ハンドラ (_SSRFBlockRedirectHandler) を利用。
    - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10 MB） と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 許可されないスキームや大きすぎるレスポンスはスキップ。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、スキーム/ホスト小文字化、フラグメント除去、クエリキーソート化。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を担保。
  - テキスト前処理: URL 削除、連続空白正規化。
  - RSS 解析: title / content:encoded / description / pubDate の扱い、pubDate のパース（UTC での正規化。失敗時は現在時刻を代替）。
  - DB 保存（DuckDB）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いることで「実際に挿入された記事ID」を返す。チャンク分割とトランザクション管理を実装。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT RETURNING で挿入数取得）。
  - 銘柄コード抽出: テキスト中の 4 桁数字を抽出し、既知コードセットと照合して重複排除して返す（extract_stock_codes）。
  - 統合ジョブ run_news_collection: 複数 RSS ソースから収集して保存、銘柄紐付けまでを一括で実行。各ソースは個別にエラーハンドリング。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤ用のテーブル DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（途中まで定義ファイルに含む）
  - スキーマ管理・初期化の基盤を導入（DataSchema.md に準拠した層設計を想定: Raw / Processed / Feature / Execution）。

- 研究（Research）モジュール（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）先の将来リターンを DuckDB の prices_daily から算出。単一クエリで取得し、データ不足は None。
    - calc_ic: ファクター結果と将来リターンを code で突合し、スピアマン順位相関（IC）を計算。データ不足（有効レコード < 3）や分散ゼロの場合は None を返す。
    - rank: 同順位は平均ランクになるよう実装（浮動小数の丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算（None 値除外）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離率（ma200_dev）を prices_daily から算出。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true range の NULL 伝播を適切に制御。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（EPS が 0 または欠損なら PER は None）。最新の report_date を取得するロジックを実装。

- API エクスポート（kabusys.research.__init__）
  - 主要関数を __all__ で公開: calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats から）、calc_forward_returns, calc_ic, factor_summary, rank。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- defusedxml を使用した RSS パースや SSRF 防止、レスポンスサイズ制限など、外部入力・ネットワーク取り扱いに関するセキュリティ対策を多く導入。

### Notes / Migration
- 環境変数のキー名、必須項目（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を .env に設定してください。Settings._require は未設定時に ValueError を投げます。
- DuckDB のスキーマは schema モジュールの DDL に基づき作成する想定です。raw_executions テーブル定義はファイルの抜粋で途中まで含まれています（今後の継続実装に注意）。
- Research モジュールは外部ライブラリ（pandas 等）に依存しない標準ライブラリ + duckdb の実装方針です。DuckDB 接続を渡して使用してください。

もし CHANGELOG に追記したい変更点（未検出の機能や修正）があれば、該当箇所のコードや要望を示していただければ更新します。