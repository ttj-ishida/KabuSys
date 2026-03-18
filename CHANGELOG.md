CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-18
-----------------

初回公開リリース。KabuSys のコア機能とデータ収集 / 研究用ユーティリティを実装しました。

Added
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - サブパッケージエクスポートを定義（data, strategy, execution, monitoring）。

- 環境設定
  - 環境変数 / .env ファイル自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出。
    - 読み込み順は OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
    - .env パースで export プレフィックス、クォート文字列、インラインコメントをサポート。
    - 既存の OS 環境変数を保護する protected 機構を備えたロードロジック。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で提供。
    - J-Quants / kabu API / Slack / DB パス等の設定プロパティを定義。
    - 入力検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
    - デフォルト DB パス：duckdb -> data/kabusys.duckdb、sqlite -> data/monitoring.db
    - 必須設定は _require() で未設定時に ValueError を投げる仕様。

- データ取得（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
    - 401 を受信した場合は ID トークン自動リフレッシュを行い 1 回リトライする仕組みを追加。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装。
    - 取得日時 (fetched_at) を UTC ISO8601 で保存し、Look-ahead Bias を防止するトレースを可能に。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、堅牢なパースを実現。

- ニュース収集
  - RSS ベースのニュース収集モジュールを実装（kabusys.data.news_collector）。
    - RSS の取得（HTTP/HTTPS）、gzip 解凍、サイズ制限（MAX_RESPONSE_BYTES=10MB）を実装。
    - defusedxml を使った安全な XML パースを行い XML Bomb 等に対策。
    - SSRF 対策：
      - URL スキーム検証（http/https のみ許可）
      - リダイレクトを事前検査するカスタム HTTPRedirectHandler（ホストがプライベートかどうか検証）
      - DNS 解決した IP を検査してプライベート / ループバック / リンクローカル等を拒否
    - URL 正規化とトラッキングパラメータ除去（utm_ 等）、SHA-256 による記事 ID 生成（先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）を実装。
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id）をチャンク分割して実装。
    - news_symbols への紐付けを一括挿入する内部ユーティリティを実装。
    - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）を実装。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を定義。

- 研究（Research）
  - 特徴量探索とファクター計算を実装（kabusys.research）。
    - feature_exploration:
      - calc_forward_returns：指定日に対する将来リターン（デフォルト horizons=[1,5,21]）を DuckDB の prices_daily から計算。
      - calc_ic：Spearman（ランク相関）ベースの IC 計算。ランキング処理（同順位は平均ランク）を含む。
      - factor_summary：各ファクター列の count/mean/std/min/max/median を計算。
      - rank：同順位を平均ランクとするランク化ユーティリティ（丸めによる ties 検出対策あり）。
      - いずれも標準ライブラリのみで実装（pandas 等に依存しない）。
    - factor_research:
      - calc_momentum：mom_1m/mom_3m/mom_6m、および 200 日移動平均乖離 ma200_dev を計算（データ不足時は None）。
      - calc_volatility：20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
      - calc_value：raw_financials から最新の財務データを取り、PER（EPS が 0 または欠損時は None）と ROE を計算。
      - すべて prices_daily / raw_financials のみを参照し、発注 API 等にはアクセスしない設計。
      - スキャン範囲にバッファを取り、休日を吸収する実装。

- DuckDB スキーマ
  - スキーマ定義モジュールを追加（kabusys.data.schema）。
    - Raw Layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
    - 各種制約（NOT NULL、PRIMARY KEY、CHECK）を設定してデータ整合性を確保。
    - スキーマは DataSchema.md に基づく 3 層（Raw / Processed / Feature）構想を反映。

- その他ユーティリティ
  - API レート制御用の内部 RateLimiter とトークンキャッシュ実装（ページネーション中でトークン共有）。
  - HTTP リクエストユーティリティにおける詳細なエラーハンドリング（JSON デコード失敗時の明示的エラー等）。
  - ロギング出力を各所に追加して稼働時のトラブルシュートを容易に。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- RSS パーサに defusedxml を使用し、XML ベースの攻撃に対策。
- RSS フェッチでの SSRF 対策を実装（スキーム検証、プライベートアドレス拒否、リダイレクト検査）。
- J-Quants クライアントのトークン自動リフレッシュ・堅牢な再試行ロジックで異常時の無限ループや不正な失敗モードを回避。

Known limitations / Notes
- research モジュールは標準ライブラリのみで実装しており、pandas 等の高速処理ライブラリは未導入です。大規模データにはパフォーマンス上の制約があり得ます。
- calc_value は現状 PER/ROE のみを返し、PBR や配当利回りは未実装です（将来拡張予定）。
- strategy と execution サブパッケージは __init__.py のみで具体的な取引ロジックや発注ラッパーは未実装です。
- DuckDB スキーマ定義は Raw Layer を中心に含まれています。Processed / Feature / Execution レイヤの完全な DDL は今後追加予定。
- 環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
- テスト時や CI 環境で .env 自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献
- 初回リリースのため、機能追加・バグ修正・改善提案は issue / pull request を歓迎します。今後のバージョンで機能拡張（戦略モジュール、発注ラッパー、Feature Layer DDL、パフォーマンス改善等）を予定しています。