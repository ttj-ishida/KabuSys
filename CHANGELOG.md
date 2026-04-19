CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

[未リリース] セクションは必要に応じて使用してください。

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション初期リリース（__version__ = 0.1.0）。
- 起動スクリプトを追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御に data/stop_requested.flag を使用。
    - 監視用 DB 接続は環境にかかわらず本番 sqlite_path を使用する旨明示。
    - DuckDB との接続を確立して SystemMonitor に渡す。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全に停止可能。
    - 実行中の PID を data/execution.pid に保持する設計を想定。
- 設定・環境管理:
  - kabusys.config: Settings クラスを導入し、各種設定（DB パス、API トークン、しきい値、環境判定など）を環境変数から取得可能に。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を検出し、.env/.env.local を自動読み込み（OS 環境変数優先）。
    - .env のパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントを考慮。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env ウィザード CLI:
  - kabusys.config_setup: 対話式ウィザードで .env を作成・更新する機能を追加（項目定義と読み書きロジックを提供）。
  - 秘匿項目はマスク表示・入力可能。
- 設定検証 CLI:
  - kabusys.validate_config: 起動前の設定検証ツールを追加。必須環境変数確認、KABUSYS_ENV/LOG_LEVEL 検査、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML がある場合）を検査。
  - --strict オプションで警告を失敗扱いにできる。
- ロギングユーティリティ:
  - kabusys.utils.logging_setup.setup_logging を追加。ルートロガーに StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。LOG_DIR/LOG_LEVEL の解決順をサポートし、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度 / CPU affinity ユーティリティ:
  - kabusys.utils.process_priority に set_process_priority / set_cpu_affinity を追加。psutil を利用して Windows と POSIX 系で優先度を設定し、失敗時は警告を出してスキップする設計。
- ポートフォリオ構築関連（純関数群）:
  - kabusys.portfolio.portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア降順ソート、スコアが全てゼロなら等配分へフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）と候補除外ロジック実装。unknown セクターは上限対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。price 欠損時のスキップ、安全弁（max_per_stock）などを実装。
  - 上記 API をまとめた kabusys.portfolio パッケージをエクスポート。
- Paper Trading 検証レポート:
  - kabusys.tools.paper_verification_report を追加。paper_trading DB をスキャンして稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定する CLI を提供。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
- 研究用ファクター計算（骨組み）:
  - kabusys.research.factor_research にモメンタム等のファクター計算関数（calc_momentum の骨子）を追加。DuckDB を用いた prices_daily/raw_financials ベースの設計。なおファイル末尾が未完（途中実装）であり、今後の実装が想定される。

Changed
- 起動時にプロセス優先度を "high" に設定する初期処理を実装（run_monitoring と run_execution の両方）。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値（0 以下や整数以外）に対してデフォルト（60秒）にフォールバックして警告を出す実装を追加。
- logging_setup: StreamHandler を stderr ではなく stdout に出力するよう変更（cron/スケジューラで stdout/stderr をまとめやすくするため）。
- config: 環境名（KABUSYS_ENV）とログレベルの許容値チェックを厳格化し、不正値は ValueError を送出するように改良。
- run_execution: paper_trading 環境では専用の SQLite を使用し、本番の SQLite と完全に分離する運用を明確化。

Fixed
- process_priority/set_cpu_affinity: 権限不足や未対応プラットフォーム時に例外で停止しないよう例外処理を追加し、警告を出力してスキップする挙動に修正。
- .env パーサー: export プレフィックス、引用符付き値、バックスラッシュのエスケープ、インラインコメントの扱いを改善してより堅牢に。

Notes / Known issues
- kabusys.research.factor_research.calc_momentum の実装がファイル末尾で未完（途中で切れている）。今後のリリースで完成予定。
- position_sizing の価格欠損（price が 0.0 の場合）に関する TODO が残っており、前日終値等でのフォールバックが未実装。
- config_setup が生成する .env はセキュリティ上 Git にコミットしないよう警告を出すが、自動的な秘匿保護は行わないため運用上の注意が必要。
- validate_config は PyYAML 未導入時に YAML 内容検証をスキップする。より厳格な CI では PyYAML を必須にする運用を推奨。

セキュリティ
- 機密情報（API トークン / パスワード）は Settings 経由で環境変数から取得し、config_setup/CLI は入力時にマスク表示を行う。しかし .env 取り扱いは運用者の責任で行ってください（.env をリポジトリにコミットしないことを強く推奨）。

ライセンス / その他
- 本 CHANGELOG はリポジトリ中のソースコードから推測して作成しています。実際のコミット履歴・差分が存在する場合はそれに沿って更新してください。