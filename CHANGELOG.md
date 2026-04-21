CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-21
--------------------

Added
- パッケージ初期リリース（バージョン 0.1.0）。
- 環境設定 / 起動関連
  - Settings クラスを実装し、環境変数を一元的に取得・検証できるようにしました。
    - 主要プロパティ: J-Quants / kabuAPI / LINE トークン、DuckDB/SQLite パス、PID/Kill フラグパス、監視しきい値、環境種別 (development/paper_trading/live) など。
    - KABUSYS_ENV・LOG_LEVEL 等の値チェックを実装。
    - PAPER_FILL_MODE と PAPER_TRADING_SQLITE_PATH など Paper Trading 向け設定を追加。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。OS 環境変数の保護（上書き禁止）や KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パースの堅牢化: export プレフィックス対応、クォート／エスケープ処理、コメントルールの実装。
  - 環境設定ウィザード CLI（config_setup）を追加。対話式で .env を作成・更新可能。
  - 設定検証 CLI（validate_config）を追加。必須環境変数チェック、パス/ログレベルチェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）を実施。--strict モードで警告を失敗扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト run_execution を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止するロジックを実装。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
  - 監視ループ起動スクリプト run_monitoring を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視は常に本番用 sqlite_path を使用する設計（環境にかかわらず本番監視 DB を利用）。
    - 停止フラグ検知、例外のログ出力、KeyboardInterrupt ハンドリングを実装。

- ログ / プロセスユーティリティ
  - 統一ログ設定ユーティリティ setup_logging を追加。
    - stdout 出力の StreamHandler と日次ローテーション (TimedRotatingFileHandler) をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - プロセス優先度 / CPU affinity 設定ユーティリティ (process_priority) を追加。
    - Windows/Linux/macOS 等の差分を吸収して優先度設定を試みる（psutil を使用）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。権限不足等はワーニングで安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を追加。
    - スコアが全て 0 の場合は等分配へフォールバックして警告。
  - risk_adjustment: apply_sector_cap（セクター集中制限の適用）、calc_regime_multiplier（市場レジームに応じた資金乗数）を追加。
    - sell_codes を指定して当日売却予定銘柄をエクスポージャー計算から除外可能。
    - "unknown" セクターはセクター上限の対象外とする挙動を採用。
  - position_sizing: calc_position_sizes を追加。
    - risk_based / equal / score の配分手法をサポート。
    - lot_size（単元株）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリングを実装。
    - スケーリング時の端数配分に再現性を持たせるロジックを実装。

- 研究・分析
  - research.factor_research モジュールを追加（モメンタム等のファクター計算のための骨組み）。
    - calc_momentum 等の関数を用意し、DuckDB 上の prices_daily テーブルを参照して計算する設計。
    - 定数やスキャンウィンドウ（1M/3M/6M、MA200、ATR20 など）を定義。

- ツール
  - tools/paper_verification_report を追加。ペーパートレード用 SQLite DB から検証レポートを生成する CLI。
    - 稼働率、注文成功率 / 送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出。
    - 閾値を定め PASS/FAIL 判定を行う（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
    - --from / --to / --db オプションで期間・DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH による指定にも対応。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- run_monitoring は monitoring 用 DB の初期化（init_monitoring_db）を行い、DuckDB も併用している。監視・分析のために sqlite3 と duckdb の接続を確保する設計。
- run_execution は paper_trading と本番 DB を明確に分離する設計になっており、MockBroker を用いた検証が可能。
- ログは stdout を主要なコンソール出力先とすることで、cron / Task Scheduler 等でのリダイレクト運用に配慮している。
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされる（パッケージ配布後の安全性・移植性を考慮）。

Authors
- KabuSys チーム（実装: コードベースより推測）

License
- 明示的なライセンス情報はコード内に含まれていません。プロジェクトの実際の LICENSE を確認してください。