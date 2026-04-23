# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更点をカテゴリ別に記載します。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更・改善
- Fixed: バグ修正
- Removed / Deprecated: 削除・非推奨

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初回公開リリース (バージョン情報: `kabusys.__version__ == "0.1.0"`)。

- 起動スクリプト / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内 data/stop_requested.flag ファイルで行う。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する点を明確化。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（ペーパートレード用クライアント）を使用し、`data/paper_trading.db` に記録して本番 DB と分離。
    - 起動前に停止フラグをチェックし、フラグありなら起動を行わない。
    - 実行中は停止フラグ検出でエンジン停止を要求する。
    - 実行プロセスの優先度を "high" に設定し、PID ファイル管理を行う。

- 設定・環境管理
  - config.py:
    - 自動 .env ロード機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。
    - ロード順: OS 環境変数 > .env.local > .env。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント扱い等）。
    - Settings クラスを導入し、環境変数取得をプロパティ化。必須チェック、値の検証（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）を実装。
    - デフォルト値と Path の expanduser を利用したパス解決を追加（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` 等）。
    - 監視・閾値設定用プロパティ（CPU/MEM/DISK 閾値、PID ファイルパス、KILL フラグ等）を追加。

  - config_setup.py:
    - 対話式ウィザードにより .env の初期作成/更新を支援する CLI を追加。
    - 必須/任意/シークレット項目の入力プロンプト、既存 .env 読み込み、保存確認を実装。
    - デフォルト値や選択肢（`KABUSYS_ENV`, `LOG_LEVEL`, `KILL_FLAG_CLEAR_ON_START` 等）を提示。

  - validate_config.py:
    - 起動前に .env と config/*.yaml の不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、プレースホルダ値警告、KABUSYS_ENV の妥当性、ログレベルチェック、DB パス存在確認（親ディレクトリ）などを実装。
    - PyYAML がない場合は YAML 検証をスキップして警告を出す。
    - `--strict` フラグで警告をエラー扱いにできる。

- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに対し StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を統一的に設定するユーティリティを追加。
    - ログ出力先（LOG_DIR）、ログレベル解決、既存ハンドラのクリーンアップ、ファイルハンドラ失敗時のフォールバック等を実装。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows (psutil の HIGH_PRIORITY_CLASS 等) と POSIX の nice 値を扱い、例外時は警告してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity 関数を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコアが全て 0.0 の場合は等金額へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジックを実装（既存保有を考慮して当日新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知のレジームは 1.0 にフォールバックし警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 単元株丸め、リスクベース・等分配・スコア配分などをサポートする株数決定ロジックを実装。
    - aggregate cap により総投資額が利用可能現金を超える場合はスケールダウンし、残余で端数（lot 単位）を割り当てるアルゴリズムを実装。
    - lot_size、cost_buffer、max_position_pct、max_utilization 等のパラメータを受け取る。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB からシステム安定性、注文成功率、リスク却下数、APIレイテンシ等を集計して検証レポートを生成する CLI を追加。
    - P95 レイテンシ計算、各種閾値（稼働率/成功率/送信率/P95）に基づく PASS/FAIL 判定を実装。
    - `--from/--to/--db` オプションをサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` により DB パス指定可能。

- リサーチ
  - research/factor_research.py:
    - DuckDB を用いたファクター計算の設計とモメンタム等の計算関数群の実装を開始（モジュール構成・定数・関数シグネチャを備える）。
    - （一部実装中断箇所あり）

### Changed
- なし（初回リリースのため既存からの変更履歴は無し）

### Fixed
- なし（初回リリース）

### Deprecated / Removed
- なし

---

補足（実装上の挙動メモ）
- run_monitoring は MONITOR_POLL_INTERVAL が不正（非整数や <=0）の場合にデフォルト 60 秒へフォールバックして警告ログを出す。
- config._parse_env_line はシングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントの扱いを考慮しており、より堅牢に .env を読み込む。
- Settings のプロパティは未設定時に ValueError を送出するもの（必須）とデフォルトを返すものが混在するため、起動前に validate_config で検証することを推奨する。
- logging_setup は標準出力を stdout にしているため、cron 等でのログリダイレクト時に扱いやすい設計になっている。

今後の予定（提案）
- research/factor_research の残り実装（calc_momentum の完了など）。
- テストカバレッジの追加（特に position sizing / sector cap / .env パーサ）。
- 実行時の observability 向上（メトリクス出力、詳細な監視イベント記録）。