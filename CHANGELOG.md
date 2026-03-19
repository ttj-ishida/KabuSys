# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

なお、この CHANGELOG はコードベースから推測して作成した初期リリースの概要です。

## [0.1.0] - 2026-03-19

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定し、サブパッケージを公開 (data, strategy, execution, monitoring)。
  - 設定 / 環境変数ロード
    - src/kabusys/config.py
      - .env ファイルと環境変数から設定を自動ロードする機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
      - プロジェクトのルート検出は .git または pyproject.toml を基準とし、__file__ から親ディレクトリを探索してプロジェクトルートを特定（配布後の動作を考慮）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
      - .env パース機能: export 構文、クォート内エスケープ、行末コメントの扱いなどに対応する堅牢なパーサを実装。
      - Settings クラスを公開 (settings)。必須キーの取得時には未設定で ValueError を送出。
      - デフォルト値/検証:
        - KABUSYS_ENV の有効値: development / paper_trading / live（不正値で ValueError）
        - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
        - デフォルトの DB パス: DUCKDB_PATH = data/kabusys.duckdb, SQLITE_PATH = data/monitoring.db
  - Data モジュール
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。
      - レート制限 (120 req/min) を守る固定間隔スロットリング _RateLimiter を実装。
      - 冪等性を考慮した保存関数（DuckDB へ ON CONFLICT DO UPDATE）を実装:
        - save_daily_quotes: raw_prices テーブルへ保存（PK 欠損行スキップ、fetched_at 記録）
        - save_financial_statements: raw_financials へ保存（PK 欠損行スキップ）
        - save_market_calendar: market_calendar へ保存（HolidayDivision を解釈）
      - HTTP リクエスト処理:
        - リトライ（指数バックオフ、最大 3 回）、408/429/5xx を対象。
        - 401 受信時は ID トークンを自動リフレッシュして 1 回のみリトライ（無限再帰回避）。
        - ページネーション対応 fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - 型変換ユーティリティ: _to_float, _to_int（安全な変換ロジック）。
      - ID トークンのモジュールレベルキャッシュを実装し、ページネーション間で共有。
    - src/kabusys/data/news_collector.py
      - RSS フィードからニュースを収集・前処理・保存するモジュールを実装。
      - セキュリティ対策:
        - defusedxml を用いた XML パース（XML Bomb 等の防御）。
        - SSRF 対策: リダイレクト時にスキームとホスト/IP の検証を行う _SSRFBlockRedirectHandler を実装。ホストのプライベートアドレス検査を実施。
        - 許可スキームは http/https のみ。
        - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズ検査（Gzip bomb 対策）。
      - URL 正規化・重複排除:
        - トラッキングパラメータ（utm_*, fbclid 等）を削除して正規化し、SHA-256（先頭32文字）で記事IDを生成。
      - テキスト前処理: URL 除去、空白正規化。
      - 銘柄コード抽出: 4桁数字パターンから known_codes に含まれるコードのみ抽出（重複排除）。
      - DB 保存:
        - save_raw_news: INSERT ... RETURNING id を用いて新規挿入IDのみ返す。チャンク分割、1トランザクションで実行。
        - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入（ON CONFLICT DO NOTHING, INSERT ... RETURNING を利用）。
      - RSS フェッチ関数 fetch_rss と統合ジョブ run_news_collection を提供（ソース単位でエラーハンドリング、known_codes による銘柄紐付け）。
    - src/kabusys/data/schema.py
      - DuckDB 用のスキーマ DDL を追加（raw / processed / feature / execution 層の定義方針）。
      - Raw レイヤ用のテーブル DDL を実装（例: raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
  - Research モジュール
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns（複数ホライズンに対応、SQL LEAD を使用）。
      - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク算出により算出、データ不足時は None を返す）。
      - ランク変換ユーティリティ rank（同順位は平均ランク、浮動小数点丸めで ties の検出誤差を抑制）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None と非有限値を除外）。
      - 設計方針: DuckDB の prices_daily テーブルのみ参照し、本番 API にはアクセスしない。
    - src/kabusys/research/factor_research.py
      - ファクター計算を実装（モメンタム / ボラティリティ / バリュー等）。
        - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（移動平均カウント不足時は None）。
        - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR 欠損時は None）。
        - calc_value: per, roe（raw_financials から最新の財務レコードを取得して結合）。
      - 各関数は DuckDB 接続を受け取り、(date, code) をキーとする dict のリストを返す。
    - src/kabusys/research/__init__.py にて主要関数を公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize 等）。
  - その他
    - 空のパッケージプレースホルダ: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py（今後の実装用に確保）。

### Changed
- 新規リリースのため変更履歴はありません（初回追加）。

### Fixed
- 該当なし（初回リリース）。

### Security
- news_collector に SSRF 対策・defusedxml 利用・レスポンスサイズ制限を導入。
- jquants_client の HTTP リトライとトークンリフレッシュ部分で例外ハンドリングを強化。

### Notes / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等は Settings からアクセスするときに必須となり、未設定時は ValueError を送出します。.env.example を参照して .env を準備してください。
- 自動 .env ロードを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に推奨）。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- J-Quants API 呼び出し時のレート制限を考慮して実行してください。クライアントは内部で 120 req/min に従うスロットリングを行いますが、大量並列実行は避けてください。

### Breaking Changes
- 該当なし（初回リリース）。

---

今後のリリースでは、strategy と execution の具象実装、monitoring の詳細、テストカバレッジや CI ワークフロー、ドキュメント（StrategyModel.md / DataPlatform.md / DataSchema.md）の整備状況に応じた変更点を記載予定です。