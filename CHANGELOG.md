Keep a Changelog に準拠した CHANGELOG.md（日本語）
======================================

すべての変更は semver に従います。初回リリースとして以下を記載します。

フォーマットの注記:
- 主要な追加(Added)、変更(Changed)、修正(Fixed)、破壊的変更(Breaking)、セキュリティ関連(Security) を区別しています。
- 日付はこのリリース作成日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース。KabuSys 自動売買システムの基本コンポーネントを実装・公開。

### Added
- 基本アーキテクチャ・起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して初期化。
    - 起動直後にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録。
    - 停止フラグを検知すると実行エンジンを停止する制御。
    - エンジンは別スレッドで起動し、PID ファイルをサポート（data/execution.pid）。
    - 起動直後にプロセス優先度を "high" に設定。

- 設定・環境関連
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を保護）。
    - env パースの細かい仕様:
      - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
      - クォートなしの値ではインラインコメント対応（直前がスペース/タブの場合に # をコメント扱い）。
    - Settings クラスで各種設定プロパティ（DB パス、PID/kill flag、閾値、paper_trading 関連設定等）を提供。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）。
  - config_setup.py:
    - 対話式 .env ウィザードを実装。初期 .env 作成・更新を支援。
    - 機密項目はマスク表示。生成される .env に対する注意喚起（Git へコミット禁止）。
  - validate_config.py:
    - 起動前検証 CLI を実装。必須環境変数や config/*.yaml の存在/パース（PyYAML が存在する場合）を検証。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティを実装。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力を自動的に無効化し、コンソール出力のみ継続。
    - stdout を使用することで cron 等からのログ収集を想定。
  - utils/process_priority.py:
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを実装（psutil ベース）。
    - 権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコアでソートして上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分。スコア全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑制するフィルタリング。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。
    - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケールダウン実装。
    - スリッページ・手数料分を cost_buffer で保守的に見積もるロジック。

- ツール類
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、--db オプションおよび PAPER_TRADING_SQLITE_PATH 環境変数に対応。

- 研究用モジュール（下地）
  - research/factor_research.py:
    - ファクター計算のスケルトンを実装（モメンタム、MA200、ATR、出来高等の計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を利用する設計方針。

### Changed
- パッケージ初版のため既存からの変更はありません。

### Fixed
- 環境変数関連の落とし穴に対する堅牢化:
  - MONITOR_POLL_INTERVAL が不正（非整数または 0 以下）の場合、デフォルト（60 秒）へフォールバックして警告を出力。
  - .env の読み込み失敗時は警告を出す（例: ファイルアクセスエラー）。
  - logging_setup はログディレクトリ作成失敗やファイルハンドラ生成失敗時にコンソールのみで継続するようにして起動不能を避ける。
- process_priority: 未対応 OS や権限不足での失敗を捕捉し警告してスキップするようにした。

### Breaking Changes
- なし（初回リリース）。

### Security
- config_setup により生成される .env に対して「絶対に Git にコミットしないこと」を明記。
- validate_config は本番（live）環境で LINE 通知設定の不足や KILL_FLAG_CLEAR_ON_START 設定の危険性を警告。

### Notes / Implementation details
- 監視（monitoring）と実行（execution）はそれぞれ Settings を使用して DB/パス等を解決。両プロセスとも起動時に set_process_priority("high") を呼ぶ設計。
- monitoring と execution の双方で init_monitoring_db(sqlite_conn) を呼び、監視用テーブルの存在を冪等に保証する。
- ExecutionEngine の risk manager 向けデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）はコード上で初期値として設定される。initial_portfolio_value はブローカーから取得する available_cash を使用。
- ポートフォリオ関連の関数群は副作用を持たない純粋関数として設計され、ユニットテストが容易な構造。

今後の予定（例）
- research/factor_research の完全実装（各ファクター計算の SQL 実装）。
- ExecutionEngine / BrokerClient の具体実装の追加と統合テスト。
- モニタリングアラート（LINE 送信等）の実装強化。
- 単体テスト・CI の追加とドキュメント整備。

---
この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートはプロジェクトのコミット履歴やリリースポリシーに合わせて調整してください。