# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
※この CHANGELOG は与えられたコードベース（src/ 以下）から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開リリース（コードベースの初期実装に相当）。以下の主要機能を実装しています。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。停止フラグ検出による安全停止、例外発生時のログ出力と継続動作を実装。
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper DB を使用し MockBrokerClient を利用する運用に対応。停止フラグの検出・エンジン停止処理、PID ファイル指定対応。

- 設定・環境変数管理
  - config.py: プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数優先）。エントリ行の堅牢なパース（export プレフィックス、クォート、エスケープ、インラインコメント処理等）。必須環境変数取得ヘルパ、各種設定プロパティ（DB パス、paper_trading 用設定、監視閾値、ログレベル、環境種別判定等）、値検証（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL など）を実装。settings インスタンスをエクスポート。

- モジュール群（ポートフォリオ・建玉・リスク調整）
  - portfolio.portfolio_builder: シグナル選定（スコア降順、タイブレーク）、等配分・スコア加重配分関数を実装。スコア全零時のフォールバックと警告出力。
  - portfolio.risk_adjustment: セクター集中上限を考慮した候補フィルタ apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。unknown セクターの扱い、ログ出力あり。
  - portfolio.position_sizing: 建玉数計算 calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" に対応）、単元株（lot_size）丸め、per-position / aggregate の上限、cost_buffer を加味した保守的見積り、可用現金を超過した場合のスケールダウンと端数処理（残差に基づく lot 単位での追加配分）を実装。

- Execution サブシステム（起動時組立て）
  - run_execution での依存コンポーネント組立て: BrokerClientFactory, OrderRepository, OrderManager, RiskManager（デフォルト RiskConfig を提供）、Reconciler, ExecutionEngine の起動フローを用意。duckdb 接続を利用。

- 監視・ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 set_process_priority、CPU affinity 固定 set_cpu_affinity を実装。権限不足や未対応 OS の場合は警告でフォールバック。
  - duckdb を利用する箇所を複数ファイルで使用（research / ai / 起動スクリプト等）。

- 研究・リサーチ機能
  - research.factor_research: momentum / volatility / value ファクター計算関数（calc_momentum, calc_volatility, calc_value）。DuckDB の prices_daily / raw_financials テーブルを用いた SQL+Python 実装。各ファクターでデータ不足時の None ハンドリング、ウィンドウサイズやバッファ日数管理を実装。
  - research.feature_exploration: 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証）、IC（スピアマン順位相関）計算 calc_ic、rank と factor_summary（基本統計量）を実装。標準ライブラリのみで実装。

- AI ニュース NLP
  - ai.news_nlp: raw_news から銘柄別のニュースを集約し OpenAI API（gpt-4o-mini）でセンチメントスコアを算出して ai_scores に書き込むための score_news 実装を想定。バッチサイズ、最大記事数・文字数トリム、JSON 出力厳格検証、リトライ（429/ネットワーク断/5xx への指数バックオフ）、スコアの ±1.0 クリップ、部分成功時の DB 更新戦略（対象コードで絞って置換）などフェイルセーフな設計を反映。ニュースウィンドウ計算 calc_news_window を実装（JST→UTC のウィンドウ変換）。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト（コマンドライン実行）。システム安定性（稼働率）、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し閾値判定（PASS/FAIL）して標準出力に整形出力。データ不足やテーブル欠如を考慮した耐障害性がある。閾値定義（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を含む。

- パッケージ情報
  - package 初期情報として kabusys.__version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数・ファイル入出力に関する堅牢性強化
  - .env 読み込みでのファイルアクセス失敗時に警告発行してスキップ。
  - MONITOR_POLL_INTERVAL の不正値検出時にデフォルトへフォールバックして警告を出力。
  - DuckDB / SQLite のクエリ実行でテーブルが存在しない場合に備えた例外処理（レポート生成時など）。

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数による API キーやパスワード取り扱いを前提（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。.env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。機密情報の扱いは運用ドキュメントに従ってください。

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際の変更履歴やリリース計画はリポジトリのコミット履歴やリリースノートに従ってください。