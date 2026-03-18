# CHANGELOG

すべての重要な変更点をこのファイルに記録します。本プロジェクトは Keep a Changelog に準拠しています。
リリースバージョンは semver を使用します。

## [Unreleased]

---

## [0.1.0] - 2026-03-18

### Added
- 初回リリース（パッケージ名: kabusys）。
- パッケージ初期化:
  - src/kabusys/__init__.py にてバージョン "0.1.0" と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env のパース機能を実装（コメント行、export プレフィックス、クォート／エスケープ、インラインコメント処理に対応）。
    - .env 読み込みの上書きルール（override/protected）を導入。OS 環境変数保護の仕組みを実装。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時等に利用可能）。
    - 必須環境変数チェック用 _require() と Settings クラスを提供。以下の設定プロパティを含む:
      - J-Quants: jquants_refresh_token
      - kabuステーション API: kabu_api_password, kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
      - Slack: slack_bot_token, slack_channel_id
      - DB パス: duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
      - システム設定: env（development/paper_trading/live のバリデーション）, log_level（DEBUG/INFO/... のバリデーション）, is_live/is_paper/is_dev ヘルパー。
- Data レイヤー（J-Quants クライアント）:
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（HTTP レスポンスのページネーション対応）。
    - レート制限管理（_RateLimiter、120 req/min 固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時は ID トークン自動リフレッシュを行い 1 回リトライする仕組み。
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
    - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - 型変換ユーティリティ: _to_float, _to_int（不正な値を安全に None に変換）。
- Data レイヤー（ニュース収集）:
  - src/kabusys/data/news_collector.py
    - RSS フィードからの記事収集機能を実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML ボム等の対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/IP のプライベートアドレス検出、リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
    - テキスト前処理（URL 除去・空白正規化）、銘柄コード抽出（4桁数字、known_codes フィルタ）。
    - DB への保存はチャンク化・トランザクションで実施。save_raw_news は INSERT ... RETURNING id で実際に挿入された記事IDを返す。news_symbols への紐付けもバルク挿入をサポート。
    - run_news_collection で複数ソースを安全に収集・保存する統合ジョブを提供（ソース単位でのエラーハンドリング）。
- Research レイヤー:
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum (mom_1m, mom_3m, mom_6m, ma200_dev)、内部で DuckDB 上の prices_daily を参照し SQL ウィンドウ関数を使用。
      - calc_volatility (atr_20, atr_pct, avg_turnover, volume_ratio)、true range の NULL 伝播制御等を考慮した実装。
      - calc_value (per, roe)、raw_financials から target_date 以前の最新財務データを取得して計算。
    - 各関数はデータ不足に対して None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、範囲限定クエリで効率化）。
    - IC 計算: calc_ic（Spearman の ρ をランク平均処理で計算、レコード不足時は None）。
    - ランク関数: rank（同順位は平均ランク、浮動小数点誤差対策に round を併用）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median を算出、None 除外）。
  - src/kabusys/research/__init__.py にて主要ユーティリティを再公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- スキーマ定義:
  - src/kabusys/data/schema.py にて DuckDB 用の DDL を実装（Raw Layer のテーブル定義を含む）。
    - raw_prices, raw_financials, raw_news の CREATE TABLE 文を提供（主キー・型制約・チェック制約を含む）。
    - raw_executions の定義の下書きを含む（execution 関連テーブルの整備予定）。
- ロギング/メトリクス:
  - 主要操作（データ取得数、保存件数、警告・例外）に対して logger を適切に出力。

### Security
- RSS / HTTP 周りで複数の安全対策を実装:
  - defusedxml による XML パース、SSRF 対策（スキーム検査・プライベート IP 検出・リダイレクト時検査）、レスポンスサイズ上限チェック、gzip 解凍後のサイズ検証。
- J-Quants クライアント: トークンの取り扱いでトークン自動リフレッシュ、再試行ポリシーを明確化。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から必須取得されるため、本番実行時は設定が必要。
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

### Known Limitations / TODO
- strategy/execution/monitoring 各パッケージは __all__ とパッケージ空ファイルが存在するが、発注・バックテスト・監視ロジックは未実装（今後のリリースで追加予定）。
- schema.py に execution 層の完全な DDL（raw_executions の続き等）は未完（ファイルに続きあり）。
- 外部依存を極力抑える設計だが、現状 defusedxml と duckdb が必要。

---

（今後のリリースでは strategy と execution の具備、モジュール間の統合テスト、さらに詳細なドキュメントや CI 運用の追加を予定しています。）