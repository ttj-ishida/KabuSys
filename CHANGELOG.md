# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新バージョン: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

初回リリース。プロジェクトの基盤機能（設定管理、起動スクリプト、ロギング/プロセスユーティリティ、ポートフォリオ構築ロジック、検証ツール、ペーパートレード検証レポート等）を追加しました。

### Added
- 基本情報
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全停止、例外発生時のログ出力と継続処理。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境に依存せず本番用 sqlite_path を使用する旨を明示。

  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - Engine を別スレッドで実行、停止フラグ検知時は engine.stop() を呼び安全にシャットダウン。
    - 起動時にプロセス優先度を "high" に設定。PID ファイルを取り扱い。

- 設定管理
  - config.py
    - Settings クラスを導入し環境変数経由の設定取得を統一。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パースの堅牢化（export プレフィックス、クォート文字列、エスケープ、インラインコメントの扱い）。
    - 各種設定プロパティ（DB パス、PID パス、しきい値、env 判定メソッド等）を提供。
    - PAPER_FILL_MODE の検証（許容値チェック）。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット入力時のマスク表示、既存値の読み込み、選択肢サポート。
    - .env をテンプレート形式で書き出し（Git へのコミット禁止コメントを含む）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL の検証、DB パスや YAML ファイルの存在/パース検証。
    - KABUSYS_ENV=live の場合に追加警告（LINE 設定や Kill Switch の扱い）。
    - --strict オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging(): stdout StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに統一設定。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで続行。
    - 既存ハンドラは一度クリアして重複を防止。

  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX を吸収したプロセス優先度設定ユーティリティを追加。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity 設定機能（任意）。
    - アクセス権限不足や未対応 OS 時は警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(), calc_equal_weights(), calc_score_weights() を追加。スコアが全て 0 の場合は等分配へフォールバック。

  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中制限（max_sector_pct）適用ロジック。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックと警告。

  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer 考慮、残差を考慮した追加配分ロジックを実装。

  - portfolio/__init__.py で上記関数を公開。

- ツール/レポート
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。--from / --to / --db オプションをサポート。

- リサーチ
  - research/factor_research.py（実装の骨子を追加）
    - モメンタム等のファクター計算のための定数定義および calc_momentum の導入（実装途中・設計方針の記載あり）。
    - DuckDB 接続を受けて prices_daily / raw_financials に基づく計算を行う設計。

### Changed
- 動作/設計上の重要点
  - 監視（monitoring）は KABUSYS_ENV に関係なく「本番」用 sqlite_path を使用する設計（run_monitoring 起動スクリプトで明示）。
  - run_execution は KABUSYS_ENV=paper_trading の際に paper_trading 用 DB を使用し、本番 DB とデータを分離するよう実装。

### Fixed / Improved
- .env 取り扱い
  - .env のパースを改良（export prefix、引用符とエスケープ、インラインコメントの扱い）し、より堅牢に読み込めるようにした。
  - .env 読み込みで OS 環境変数を保護する仕組み（protected set）を導入。明示的に上書きする .env.local のサポート。

- ロギング
  - setup_logging が既存ハンドラの二重登録を防止するよう改善。
  - ログディレクトリ作成やファイルハンドラ生成に失敗してもコンソールログのみで継続する耐障害性を追加。

- プロセス優先度
  - set_process_priority/set_cpu_affinity は権限不足や未サポート環境で安全にフォールバックし、警告ログを出すようにした。

- 発注数量計算
  - calc_position_sizes のスケーリング処理で単元丸め・残余配分の扱いを改善し、可再現性を確保するための安定ソートを導入。

- 実行/監視の停止処理
  - run_execution/run_monitoring ともに stop フラグ検知で安全に停止する実装強化と、例外時のログ保護を追加。

### Security
- config_setup の出力テンプレート・ウィザードにおいてシークレットは表示時にマスクし、.env を Git にコミットしないよう注意喚起を追加。

### Docs / Developer Notes
- 多くのモジュールに docstring を追加して挙動や入力/出力、設計意図を明示（例: portfolio、research、utils 等）。
- validate_config による事前チェックフローを用意し、起動前に設定不備を検出しやすくした。

---

今後の予定（例）
- research/factor_research のファクター実装完了
- ExecutionEngine / BrokerClient 関連の統合テストおよびモックの整備
- 単体テスト・CI の追加（現在の差分はコード本体中心の実装）
- 監視・アラートの LINE 通知統合

もし特定ファイルや変更点をより詳細に記載してほしい場合は、対象箇所を指定してください。