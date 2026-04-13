# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。

全般的な注記:
- 日付はコードベースから推測して付与しています。
- 記載はソースコードの実装とドキュメント文字列から推測した機能追加・修正点に基づきます。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-13
初回リリース。本リポジトリは日本株自動売買システム「KabuSys」の基礎コンポーネント群を含みます。

### Added
- 基本情報
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境(KABUSYS_ENV)が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）に記録するよう分離。プロセス優先度設定、DB 初期化（監視テーブルの冪等初期化）、Broker クライアントの生成、ExecutionEngine の組み立てと run_session を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理
  - config.py: 環境変数/.env 自動読み込み機能を追加。プロジェクトルートを .git / pyproject.toml から探索して .env/.env.local を読み込み、OS 環境変数を上書きしないための保護機構を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。環境変数のパースはクォートやエスケープ、コメントに対応。各種設定（DB パス、PID ファイルパス、閾値、環境モード判定など）を提供する Settings クラスを実装。
- モニタリング / 運用ツール
  - monitoring_db の初期化を呼ぶフローを run スクリプトに組み込み（冪等的に監視テーブルを保証）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定を出力。P95 計算、SQL の存在チェックや OperationalError に対するフォールバックを含む。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。既存保有のセクター別エクスポージャー計算、"unknown" セクターの取り扱い、未知レジーム時のフォールバックを含む。
  - portfolio/position_sizing.py: 発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金内にスケーリング）、cost_buffer を用いた保守的見積り、残余キャッシュを用いた端数配分ロジックを含む。
- 研究（Research）モジュール
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を利用したファクター計算を実装。モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、ATR%)、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を提供。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン）、IC（Spearman 相関）計算、ファクター統計サマリ、rank（同位の平均ランク処理）を実装。外部ライブラリに依存しない純粋 Python 実装。
  - research.__init__: 研究系ユーティリティを公開（zscore_normalize を外部モジュールから再エクスポート）。
- AI / NLP
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）に送って銘柄ごとのセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。機能：
    - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算。
    - 記事集約（銘柄ごとに最大記事数・文字数をトリム）。
    - 最大 20 銘柄単位でバッチ送信、JSON Mode を期待する厳密な応答フォーマット。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ（上限回数あり）。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ。
    - 書き込みは対象コードに限定して DELETE → INSERT を行い、部分失敗時に既存データを保護。
    - API キー未設定時は ValueError を送出。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）設定ユーティリティを実装。set_cpu_affinity による CPU affinity 固定機能も提供。未対応 OS / 権限不足時は警告を出してスキップ。
- パッケージ構成
  - 複数モジュール（portfolio, research, ai, utils, tools 等）を __all__ 等で適切にエクスポート。

### Changed
- 実行フロー
  - run_monitoring/run_execution で起動時にプロセス優先度を High（または指定）に設定する処理を追加し、優先度設定でエラーが起きてもログに警告して継続するようにした。
- DB ハンドリング
  - monitoring 用 DB 初期化をエントリポイント側で明示的に行う（init_monitoring_db を呼ぶことで監視テーブルの存在を保証）。
- 設定読み込みの優先順位
  - .env 自動読み込みを OS 環境変数 > .env.local > .env の順で行う（.env.local は .env を上書き可能）。既存 OS 環境変数は protected として上書きを防止。

### Fixed
- 環境変数パースの堅牢化（config._parse_env_line）
  - export プレフィックス対応、クォートあり/なしでのエスケープとインラインコメント処理、無効行のスキップ等を実装して .env パースの信頼性を向上。
- MONITOR_POLL_INTERVAL の検証（run_monitoring._get_poll_interval）
  - 0 以下や不正な文字列を指定した場合に警告してデフォルトへフォールバックするようにし、time.sleep への不正な値渡しを防止。
- calc_score_weights のフォールバック
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックし、警告ログを出すようにした。
- position_sizing の堅牢化
  - 価格が欠損（None / <= 0）の銘柄をスキップするように修正し、単元株処理や aggregate cap スケーリングで不正な値を扱わないようにした。端数配分における安全弁（_max_per_stock の上限確認）を追加。
- research.rank の同順位処理
  - 同順位（ties）は平均ランクを割り当てる実装にして安定性を確保。丸め（round(v, 12)）で浮動小数による誤差を抑制。
- ai/news_nlp のフェイルセーフ
  - API キーなし、レスポンスの不整合、API エラー時のリトライとスキップによって、部分失敗でもプロセス全体が停止しないように実装。

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）から解決し、未設定時は明示的にエラーを出すことで誤った無認証呼び出しを防止。

---

その他注記:
- 多くの関数は DuckDB / SQLite の特定テーブル（prices_daily, raw_financials, raw_news, trade_logs, risk_logs, system_status, ai_scores 等）を参照するため、実運用ではスキーマ整備とサンプルデータが必要です。
- 設計ドキュメント（コメント内参照: PortfolioConstruction.md, StrategyModel.md 等）に準拠した実装方針が見られます。今後はドキュメントとテストケースを整備することで堅牢性をさらに高めることを推奨します。