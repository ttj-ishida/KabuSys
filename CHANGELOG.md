CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

v0.1.0 - 2026-04-19
------------------

Added
- 初回リリースを公開。
- 実行/監視用起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を使用して本番 DB と完全分離する設計。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 停止制御用フラグファイル（data/stop_requested.flag）および PID ファイル（data/execution.pid）を使用したグレースフルシャットダウンに対応。
    - スレッドで ExecutionEngine.run_session を実行し、停止フラグ検知で engine.stop() を呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0/負数はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグ検知でループを終了、KeyboardInterrupt にも対応。

- 設定/環境管理
  - config.py
    - Settings クラスを提供し、環境変数経由でアプリ設定にアクセス可能。
    - .env 自動読み込み機能を実装（プロジェクトルートの判定は .git または pyproject.toml を基に行う）。
    - auto-load の無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）サポート。
    - 各種プロパティを実装（J-Quants、kabu API、DB パス、paper_trading のパラメータ、監視閾値、環境・ログ設定判定メソッド等）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加（python -m kabusys.config_setup）。
    - 既存 .env 読み取り・確認・保存機能を提供。シークレット項目はマスク表示。

- 設定検証 CLI
  - validate_config.py
    - .env および config/*.yaml の存在・基本妥当性を確認する CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース検査（PyYAML がインストール済みの場合）、本番環境向けガードを実施。
    - --strict オプションで警告を失敗扱いにするモードを提供。

- ロギング/プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを提供。
    - LOG_LEVEL / LOG_DIR の解決ロジック、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）の統一 API を提供。Windows と POSIX（Linux/Mac/FreeBSD）を吸収。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
    - 権限不足や未対応プラットフォーム時には警告を出してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート（score 降順、signal_rank でタイブレーク）と上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"／"equal"／"score"）に応じた発注株数計算。lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash）に応じたスケーリングと残差処理を実装。
    - cost_buffer による保守的見積り（手数料/スリッページの概念）に対応。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を使ったモメンタム・ボラティリティ等のファクター計算モジュールの骨格を追加。
    - calc_momentum のインターフェイスと定数が含まれる（詳細実装はファイル末尾で継続予定）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード向け検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - デフォルト DB は data/paper_trading.db。--db で上書き可能。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出し、事前定義された閾値（稼働率 >= 99%、fill_rate >= 90% 等）に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ（ISO8601 UTC 形式）対応。

Misc / Other
- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。
  - package-level __all__ に主要サブパッケージ名を列挙。

Notes / Known limitations
- research/factor_research.calc_momentum の実装が途中で終わっている（ファイル末尾が不完全）。ファクター計算は今後の実装で完成予定。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみとなる挙動に注意。
- process_priority:
  - プラットフォーム依存のため、全ての OS で完全に同一の動作を保証していない（未対応 OS はスキップして警告）。
- config の .env 自動ロードはプロジェクトルートを特定できない場合はスキップされる。テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- calc_position_sizes の lot_size は現在全銘柄共通。将来的に銘柄別 lot_map 対応を検討。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。

Upgrade notes
- 初回リリースのため、既存ユーザーがいる場合は .env / config/*.yaml の準備、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の設定、およびデータフォルダ（data/, logs/ 等）の作成を推奨します。
- run_execution/run_monitoring 実行前に validate_config.py による検証を推奨:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

Acknowledgements
- 本リリースはコア機能の骨格（起動スクリプト、設定管理、ポートフォリオ構成、ユーティリティ、検証ツール）を提供します。今後、StrategyModel や ExecutionEngine 本体、ファクター計算の完全実装、テストカバレッジの追加を進めていきます。