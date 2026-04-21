CHANGELOG
=========

全般
-----
このファイルは「Keep a Changelog」形式に準拠しています。
リリース日付はリポジトリの現行コードから推測して記載しています。

Unreleased
----------
- 特になし。

[0.1.0] - 2026-04-21
-------------------
Added
- 初回公開リリースを追加。
- 実行スクリプト
  - run_execution.py: 実行エンジン (ExecutionEngine) 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使用し、data/paper_trading.db に記録することで本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と実行 pid ファイル (data/execution.pid) を利用した安全な停止制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト60秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して記録する設計。
- 設定・環境管理
  - config.py: Settings クラスを追加し、環境変数および .env/.env.local からの自動読み込みロジックを実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の読み込み順は OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス, PID/KILL フラグ, モニタ閾値, 環境判定 等）。
    - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 主要設定項目のプロンプト、既存 .env の読み込み、書き込みロジックを提供。
- 設定検証ツール
  - validate_config.py: CLI による設定検証を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの追加ガードを実装。
    - --strict モードを追加（警告も FAIL として扱う）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログレベル・ログディレクトリ解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収した実装。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。psutil によるアクセスエラー時は警告でスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが0のとき等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別集中制限ロジック（既存保有と当日売却予定を考慮）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは警告の上で 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer による保守的見積り、残余キャッシュを利用した補正配分を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - P95 計算、期間フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
- 研究モジュール（骨子）
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム等の仕様・定数を定義、calc_momentum のインターフェースを用意）。DuckDB 接続を受ける設計。※ファイル末尾で記述が途切れています（実装継続の余地あり）。
- パッケージ情報
  - __init__.py にバージョン 0.1.0 を設定。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Usage highlights
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。配布後にプロジェクトルートが特定できない場合は自動ロードがスキップされます。
- 本番運用時は KABUSYS_ENV=live の設定と LINE 通知設定等を慎重に確認してください（validate_config がガード、注意喚起を行います）。
- run_monitoring は監視データを書き込む DB に本番 sqlite_path を常に使用する設計です。run_execution は paper_trading 時に専用 DB を使用して本番 DB と分離します。
- research/factor_research.py の一部実装が途中で切れているため、ファクター計算の完全実装は今後の作業が必要です。