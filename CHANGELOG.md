# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]

### Added
- 全体
  - 初期機能群を追加。アプリケーションの主要サブシステム（実行エンジン、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、ツール）を収録。

- 実行/エンジン
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を統合。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動処理を実装。
    - 停止フラグ (data/stop_requested.flag) を監視し、安全にエンジンを停止する仕組みを実装。
    - プロセス優先度を最初に High に設定。

- 監視
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、値検証あり）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視用 DB 初期化を実行）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - check_once() 実行中の例外はログに記録して次のポーリングへフォールバック。

- 設定管理
  - kabusys.config.Settings を追加。
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と上書き/保護ルール（OS環境変数は protected）。
    - 環境変数のパースを強化（export プレフィックス、クォート、エスケープ、インラインコメント処理対応）。
    - 必須環境変数の検出 (_require) とバリデーション（KABUSYS_ENV, LOG_LEVEL 等の妥当性検査）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視閾値（CPU/MEM/DISK）、PID/kill flag パスなどのプロパティを提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。

- ポートフォリオ構築
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソートと上位抽出（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。全スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 銘柄ごとの発注株数算出ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position と aggregate のキャップ、cost_buffer による保守的見積り、合計が利用可能現金を超えた場合のスケーリングと端数再配分ロジックを実装。
    - 価格欠損や価格 <= 0 の銘柄処理やログ出力を考慮。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームは 1.0 でフォールバックし WARNING 出力。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: mom_1m/3m/6m と MA200 乖離率を DuckDB SQL ベースで計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率を計算（NULL 伝播を適切に扱う）。
    - calc_value: raw_financials から最新の財務数値を取得し PER/ROE を算出（target_date 以前の最新レコード取得）。
    - いずれもデータ不足時は None を返す等の堅牢性を確保。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得（horizons 検証あり）。
    - calc_ic: Spearman ランク相関（IC）計算。必要最小レコード数の検査と None ハンドリング。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と、基本統計量（count/mean/std/min/max/median）を計算。
    - 実装は外部依存を避け、標準ライブラリと DuckDB SQL のみで完結。

- ニュースNLP（AI スコアリング）
  - kabusys.ai.news_nlp を追加（ニュース記事を OpenAI API でセンチメントスコア化して ai_scores に書き込む設計）。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）用 calc_news_window を実装。
    - score_news: 処理フローの設計（記事集約、バッチ送信、リトライ、JSON レスポンス検証、スコアクリップ、DB への置換挿入）を反映。
    - API キー未設定時の明示的エラー、最大記事数／文字数のトリム制御、バッチサイズ等の定数設定を実装。
    - （注）大枠実装と堅牢化方針を盛り込んでいるが、外部 API 呼び出し周りの実装は環境に依存するため注意。

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority: Windows / POSIX の差分を吸収してプロセス優先度を設定。対応 OS の限定と例外処理（権限不足等）によるフォールバックを実装。
    - set_cpu_affinity: 指定コア数で CPU affinity を固定するユーティリティ。引数検証と例外フォールバックを実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill/send）、リスク却下数、平均/最大/P95 レイテンシ等の指標を SQLite（paper_trading DB）から集計して標準出力に整形表示。
    - データがない場合やテーブル未作成時の sqlite3.OperationalError を捕捉して N/A 表示やフェイルセーフな挙動を実現。
    - コマンドライン引数 --from/--to/--db をサポート。

### Changed
- プロセス起動フローで最初にプロセス優先度を設定するように統一（run_monitoring/run_execution）。
- .env 読み込みの既定動作:
  - 自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能にし、プロジェクトルートが検出できない場合はスキップする安全策を導入。
  - OS 環境変数は保護され、.env.local で上書き可能だが protected なキーは上書かない。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や文字列）に対するフォールバック処理を追加。タイムスリープに渡せない値を検出してログで警告しデフォルト値を使用する仕様に。

## [0.1.0] - 初回リリース
- 初期公開リリース。上記の機能群（実行エンジン、監視、設定管理、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、検証ツール）を含む。

---

注意:
- 本 CHANGELOG は与えられたコードスナップショットから推測して作成しています。実装の細部や未表示のファイル（例: ExecutionEngine の内部実装や SystemMonitor の詳細、news_nlp の一部未表示箇所など）により、実際の変更履歴と差異がある可能性があります。必要であれば各モジュールの実装箇所に基づいてさらに細かい項目に分割できます。