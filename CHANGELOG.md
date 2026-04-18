# CHANGELOG

All notable changes to this project will be documented in this file.
この CHANGELOG は Keep a Changelog の形式に準拠します。
現在のバージョン: 0.1.0

※ リリース日には本スナップショットの作成日を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite(DB) を使用し、本番 DB と隔離して MockBrokerClient を利用する設計（環境に応じたブローカークライアント生成を BrokerClientFactory が担当）。
    - エンジンはスレッドでデーモン実行され、プロジェクトルートの data/stop_requested.flag を監視して安全停止可能。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告出力。
    - Monitoring は KABUSYS_ENV に関わらず常に本番の sqlite_path を使用する（意図的に本番監視 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境変数管理
  - config.py
    - Settings クラスを実装。各種環境変数をプロパティで取得（J-Quants、kabu API、LINE、DB パス、監視閾値、ログレベルなど）。
    - .env 自動読込機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。.env, .env.local の順で読み込み、OS 環境変数の保護機構あり。
    - .env の柔軟なパース（export プレフィックス、クォート、エスケープ、インラインコメントの取り扱い）に対応。
    - `paper_fill_mode` のバリデーション（"instant"|"partial"|"never"|"reject"）。
- 設定のヘルスチェック / ウィザード
  - validate_config.py
    - 起動前に .env および config/*.yaml の存在と基本的整合性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース確認（PyYAML が存在する場合）、本番環境向けの追加ガードを実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - 秘匿値マスク、選択肢用の入力、既存 .env の読み込み・再利用、保存確認を提供。
    - .env ファイルのテンプレート生成ロジックを提供。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - 同点のタイブレーク（score 降順、signal_rank 昇順）を明確に定義。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有を基にセクター別エクスポージャーを算出し、上限（デフォルト 30%）を超えるセクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）丸め、per-position 上限・aggregate cap、コストバッファ考慮、利用可能現金に応じたスケーリングを実装。
    - risk_based 方式では stop_loss_pct と risk_pct を用いた株数算出。
    - 価格欠損時のスキップやログ出力を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log, 30日保持）をルートロガーに設定。
    - 既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを考慮。
    - デフォルトログレベルは環境変数 LOG_LEVEL または "INFO"。
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）のユーティリティを実装。
    - Windows / POSIX を吸収する実装（psutil 利用）。権限不足や未対応 OS では警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシなどを集計して PASS/FAIL を判定する。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - --from / --to / --db オプションにより期間・DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を尊重。
- リサーチ基盤（計算モジュールの骨格）
  - research/factor_research.py
    - モメンタムやボラティリティ等のファクター計算を行う設計を開始（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針を定義）。
    - 定数・設計意図（窓幅、スキャン期間等）を明文化。

### Changed
- なし（初回リリースにつき変更履歴なし）

### Fixed
- なし（初回リリースにつき修正履歴なし）

### Notes / 重要な挙動
- Monitoring（run_monitoring.py）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用 monitoring.db）を使用します。意図的な挙動なので環境切り替えの際は注意してください。
- Execution（run_execution.py）は settings.is_paper に応じて別 DB（data/paper_trading.db）を利用し、発注実績を本番 DB と分離します。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。配布後や CWD に依存しない挙動を目指しています。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギングは標準出力（stdout）を併用するため、cron 等でのリダイレクト運用を想定しています。
- process_priority/set_cpu_affinity は psutil と OS 権限に依存します。権限不足時は警告でスキップします。

### 環境変数（主なものとデフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 値: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- MONITOR_POLL_INTERVAL (default: 60)
- PAPER_FILL_MODE (default: instant) — instant | partial | never | reject
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
- KILL_FLAG_CLEAR_ON_START (default: 0)

### Migration / Usage
- 初回セットアップ:
  1. python -m kabusys.config_setup を実行して .env を作成
  2. python -m kabusys.validate_config で設定を検証
- 監視起動:
  - python -m kabusys.run_monitoring
  - 短期的にポーリング間隔を変更するには MONITOR_POLL_INTERVAL を設定
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading モードではペーパートレード DB に結果が記録される
- Paper trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

（初回リリースのため過去差分はありません。今後の変更はこのファイルに追記します。）