# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。

## [0.1.0] - 初回リリース
リリース: 初期バージョン（__version__ = 0.1.0）

### 追加 (Added)
- 全体
  - パッケージ初期実装を追加。自動売買システム KabuSys の基本コンポーネント群を提供。

- 実行 / 監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して MockBrokerClient を利用する挙動をサポート。
    - 停止用フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) による起動・停止制御に対応。
    - ExecutionEngine を別スレッドで実行し、安全に停止するためのループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックし警告を出力。
    - 監視 DB 初期化を行い、Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグの検知でループを終了。KeyboardInterrupt による終了もハンドリング。

- 設定管理
  - config.py:
    - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env/.env.local の読み込み順（OS環境変数 > .env.local > .env）を実装。上書き制御 (override, protected keys) に対応。
    - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等をサポート）。
    - Settings クラスを実装し、アプリで使用する設定値（DB パス、API トークン、ログレベル、しきい値等）をプロパティとして提供。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / SQLITE_PATH 等のデフォルトを定義。

- 設定検証 / ウィザード
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がある場合）を実行。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番 (live) 時のガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - config_setup.py: .env 作成・更新の対話型ウィザードを追加。
    - J-Quants / kabu API / DB パス / LINE 通知 / LOG_LEVEL / Kill Switch などの項目を対話的に設定し .env を生成。
    - 既存の .env を読み込んで Enter で再利用可能。シークレット項目はマスク表示。

- ロギング / プロセス設定ユーティリティ
  - utils/logging_setup.py:
    - setup_logging() を提供。ルートロガーに stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラを設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力を無効化して継続。
    - StreamHandler は stdout を使用（cron 等での出力管理を考慮）。
  - utils/process_priority.py:
    - set_process_priority(level) を実装し Windows / POSIX（Linux, macOS 等）の差分を吸収。権限不足などは警告でフォールバック。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は何もしない）。コア数が利用可能数を超える場合の扱いも考慮。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates(): score 降順、同点は signal_rank 昇順で上位 N を返す。
    - calc_equal_weights(): 等金額配分（1/N）。
    - calc_score_weights(): スコア比率で重み付け。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): 既存保有のセクター比率が max_sector_pct を超えている場合、そのセクターの新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method に応じて発注株数を計算（"risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮。コストバッファ (cost_buffer) を使った保守的な投資額見積り、合計超過時のスケーリングと残差に基づく追加配分ロジックを実装。
    - 価格欠損時のスキップ、ログ出力により欠損を通知。

- Paper trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB から検証レポートを生成するスクリプトを追加（--from, --to, --db オプション対応）。
    - 指標: 稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、API レイテンシ（avg, max, P95）。
    - P95 計算実装、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - DB のテーブル欠如に対するフォールバック（OperationalError を捕捉して N/A を扱う）。

- リサーチ / ファクター計算（着手）
  - research/factor_research.py:
    - モメンタム等のファクター計算モジュールを追加（設計に基づく）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - （ファイル末尾でモメンタム計算の実装が開始されています）

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- なし

注:
- .env ファイルは機密情報を含むため、README 等で必ず Git にコミットしない旨を案内する設計（config_setup.py のヘッダに記載）。
- 実運用時は KABUSYS_ENV や KILL_FLAG_CLEAR_ON_START 等の設定を慎重に扱うこと（validate_config の警告を参照のこと）。

---

今後の予定（例）
- ExecutionEngine / BrokerClient の具体実装とテストの追加
- ファクター計算の完全実装と検証（research/factor_research.py の続き）
- 単体テスト・CI 設定、ドキュメントの整備（README・運用手順）