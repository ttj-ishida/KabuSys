CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式で記述しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

Unreleased
----------

Added
- run_monitoring:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能に（デフォルト 60 秒）。無効値（0/負数/数値以外）は警告を出してデフォルトにフォールバックする実装を追加。
  - 停止制御ファイル（data/stop_requested.flag）を監視して安全にループ終了できる仕組みを追加。
  - 監視モジュールは環境（KABUSYS_ENV）に依らず本番 sqlite_path を使用する仕様に明示的に固定。

- run_execution:
  - KABUSYS_ENV=paper_trading 時に MockBrokerClient を利用し、paper_trading 用の専用 SQLite（data/paper_trading.db）に記録するよう実装。
  - エンジン起動前に停止フラグを確認し、既に立っていれば起動せず終了する安全処理を追加。
  - ExecutionEngine をデーモンスレッドで実行し、停止フラグを検知すると engine.stop() を呼び出して整然と停止させる実装。

- 設定まわり（config, config_setup, validate_config）:
  - プロジェクトルート自動検出（.git または pyproject.toml 基準）を実装し、.env ファイルの自動読み込みを行う（.env → .env.local、OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント扱いの改善）。
  - 対話式ウィザード（config_setup）を実装し、.env の初期作成・更新を支援。機密項目はマスク表示、既存値の再利用、保存前の確認を提供。
  - validate_config CLI を実装。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）を行う。--strict オプションで警告を FAIL 扱いにできる。

- 設定モデル（Settings クラス）:
  - 多数の設定プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / PID/KILL フラグ等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV/LOG_LEVEL の妥当性チェックを実装。
  - paper_trading 用の paper_sqlite_path、pid_file_path, kill_flag_path などファイルパスのプロパティを追加。

- ロギング（utils.logging_setup）:
  - 共通のセットアップ関数 setup_logging を実装。コンソール出力（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
  - LOG_DIR 環境変数 / 引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバックを追加。

- プロセス優先度 / CPU アフィニティ（utils.process_priority）:
  - Windows と POSIX（Linux/Mac等）で差分を吸収しつつプロセス優先度を設定するユーティリティを実装。例外時は警告を出してスキップ。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（権限不足等は警告を出してスキップ）。

- ポートフォリオ構築（kabusys.portfolio）:
  - 候補選定 select_candidates（スコア降順・タイブレークロジック）を実装。
  - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）を実装。
  - セクター集中制限 apply_sector_cap を実装（既存保有からセクター比率を計算し上限超過セクターの新規候補を除外、"unknown" セクターは上限査定除外）。
  - レジーム乗数 calc_regime_multiplier（bull/neutral/bear マップ、未知レジームはログ警告のうえ 1.0 フォールバック）を実装。
  - 株数決定 calc_position_sizes を実装。allocation_method に応じた計算（risk_based / equal / score）、単元株（lot_size）丸め、単銘柄上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積り）の考慮などを提供。

- Paper Trading 検証ツール（tools.paper_verification_report）:
  - ペーパートレード DB を解析してシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg / max / P95）を算出する CLI を実装。
  - P95 計算、期間指定（--from/--to）、DB パス指定（--db / 環境変数）に対応。閾値（稼働率・成功率・送信率・P95）で PASS/FAIL 判定を行う。

Changed
- run_monitoring / run_execution 起動時に最初に set_process_priority("high") を呼び出すように変更（高優先度での実行を意図）。
- ログ出力レベルの解決順を明示（引数 > 環境変数 > デフォルト）。
- StreamHandler を stdout に固定（stderr ではなく stdout を使用）し、cron 等からのリダイレクト運用を想定。

Fixed
- .env 読み込み時にファイルオープン失敗時の警告を追加し、例外でプロセスが停止しないよう改善。
- settings における不正値入力時の明確なエラーメッセージ（ValueError）を追加。

0.1.0 - 2026-04-24
------------------

Initial release — 基本機能の実装
- コア:
  - プロジェクトメタデータとバージョンを __version__ = "0.1.0" として設定。
- 起動スクリプト:
  - run_execution: ExecutionEngine 起動フロー、ブローカークライアントの生成（BrokerClientFactory）、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、デーモンスレッドでの実行、停止フラグによる制御を実装。
  - run_monitoring: SystemMonitor の初期化とポーリングループ、DB 初期化、停止フラグ検知処理を実装。
- 設定・運用:
  - Settings クラスによる環境変数ラッパーを提供。多くの設定プロパティ（DB パス、API トークン、監視しきい値など）を網羅。
  - .env 対応・自動読み込み、config_setup ウィザード、validate_config 検証 CLI を実装。
- ログ / プロセス管理:
  - 共通ログセットアップ、ファイルローテーション、プロセス優先度制御ユーティリティを実装。
- ポートフォリオ構築:
  - 候補選定、配分（等金額/スコア加重）、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出（リスクベース等）を実装。
- ツール:
  - Paper Trading 検証レポート生成ツールを実装。
- 研究用コード:
  - factor_research モジュール（ファクター計算の枠組み・定数）を実装（モメンタム等、計算ロジックの雛形を含む）。

Notes
-----
- 本 CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴・タグ付けと差異がある場合があります。  
- 追加のリリースや修正があればこのファイルを更新してください。