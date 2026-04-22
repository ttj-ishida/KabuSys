# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- セキュリティ (Security)

最新変更は下から上へ記載してください。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-22
初回公開リリース。本リリースでは自動売買システムのコアユーティリティ、実行・監視ランチャー、設定管理、ポートフォリオ構築、リスク制御、検証ツール、各種ユーティリティを実装しました。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient を選択（本番 DB と完全分離）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイルの扱いをサポート。
    - スレッドでエンジンを実行し、停止フラグ検知時に安全に停止。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用（監視 DB の初期化含む）。
    - 停止フラグ検知でループを終了。

- 設定管理 / ユーティリティ
  - config.py: Settings クラスを導入。
    - .env 自動読み込み（.env, .env.local、OS 環境変数優先の挙動）。
    - .env パースの強化（export プレフィックス、クォート内エスケープ、インラインコメント処理）。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / PID / Kill Switch / 監視閾値 / 環境判定 等）。
    - PAPER_FILL_MODE の検証、paper_sqlite_path 等のデフォルト。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 既存値の読み込み、シークレットマスク表示、選択肢サポート、.env への安全な書き込み機能を提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パスや config/*.yaml の存在/パースを検証。
    - --strict モードで警告を FAIL 扱いにできる。

- ログ / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、既定 30 日）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定、ファイルハンドラ作成失敗時のフォールバック動作。
  - utils/process_priority.py:
    - set_process_priority(level) で Windows/Linux（POSIX）向けに抽象化して優先度設定を実行。
    - set_cpu_affinity(cpu_count) を追加し、プロセスの CPU affinity を設定可能。
    - アクセス権限不足や未対応 OS に対する安全なフォールバックを実装。

- ポートフォリオ構築 / リスク調整 / ポジションサイズ
  - portfolio/portfolio_builder.py:
    - select_candidates(): スコア降順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights(), calc_score_weights(): 等重・スコア加重の重み計算（全スコア 0 の場合は警告して等重にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター毎のエクスポージャーを計算し、上限超過セクターの新規候補を除外（sell_codes による除外対応）。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数を提供（bull/neutral/bear、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に応じた株数決定を実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、集計上限（available_cash）によるスケーリング機構を実装。
      - cost_buffer を使った保守的見積り、スケーリング後の残差分配ロジック（fractional remainders）を実装。

- 実行周辺コンポーネント（execution パッケージとの連携）
  - 実行エンジン起動時に BrokerFactory によりブローカークライアントを生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動するワークフローを提供。
  - RiskManager に既定の RiskConfig 値（max_position_pct=0.20 等）を設定。

- 監視・検証ツール
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視テーブルの冪等な初期化を実現。
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite を読み、稼働率、注文成功率、送信率、P95 レイテンシ等を計算してレポートを出力。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定し PASS/FAIL を出力。
    - 日付フィルタ（--from/--to）、DB パスのオーバーライド（--db / 環境変数）に対応。

- 研究用モジュール（研究・因子計算）
  - research/factor_research.py: Momentum 等のファクター計算モジュールを追加（DuckDB 経由で prices_daily 等を参照する設計）。（実装途中の関数あり）

- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- ロギングのデフォルトは stdout を用いる（cron 等で stdout/stderr を一本化する運用に配慮）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に探索し、CWD に依存しない動作に変更。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を警告してデフォルトにフォールバックする堅牢化を行った。

### Fixed
- process_priority / set_cpu_affinity で権限不足や未対応プラットフォームの場合に例外を露出させず警告してスキップするように修正。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてもプロセスが続行するように改善。
- .env パーサーの引用符内エスケープ処理やインラインコメント処理を強化し、より現実的な .env 記述への対応を追加。

### Removed
- 該当なし

### Security
- JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等のシークレットは .env に保存する設計だが、config_setup にて .env を Git にコミットしないよう注意喚起を記載。

---

注:
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴・コミットメッセージとは差異がある場合があります。