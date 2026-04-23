CHANGELOG
=========

この CHANGELOG は Keep a Changelog の書式に準拠しています。  
以下の内容は提供されたコードベースを解析して推測した変更点・特徴を記載したものであり、実際のコミット履歴ではありません。

[Unreleased]
------------

- （該当なし）

[0.1.0] - 2026-04-23
--------------------

Added
- プロジェクト初期リリース相当の機能群を追加（パッケージバージョン: 0.1.0）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル data/stop_requested.flag を検知すると安全にループを終了する。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定してから起動。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と分離。
    - 起動時に実行 PID を data/execution.pid に保存/管理する想定（pid_file の取り扱い）。
    - 停止フラグ検知で ExecutionEngine.stop() を呼んで安全停止。
    - プロセス優先度を "high" に設定してから起動。
- 設定・環境管理
  - config.py: 環境変数 / .env ファイルの自動読み込み機能（.env, .env.local）と Settings クラスを実装。
    - プロジェクトルート（.git または pyproject.toml を探索）に基づく .env 自動読み込み。
    - 必須項目取得時の _require()、PAPER_FILL_MODE 等の入力検証、各種パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）やフラグのデフォルト値を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を提供。
    - 秘匿項目はマスク表示、選択肢・デフォルトをサポート。保存時は .env ファイルを生成。
  - validate_config.py: 起動前の設定検証 CLI を提供。
    - 必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在や YAML パース（PyYAML インストール時）を検証。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ初期化ユーティリティ。
    - StreamHandler は stdout を使用、TimedRotatingFileHandler で日次ローテーション（30 日保持）。
    - 既存ハンドラを上書きして二重登録を防止。
    - LOG_DIR 環境変数や引数で出力先を変更可能。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度 / CPU affinity 設定。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応した nice / priority 設定処理。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity() を提供。
    - 権限不足や未対応プラットフォーム時は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(): BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights(), calc_score_weights(): 等分配・スコア加重の重み計算（全スコア 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクターごとの既存露出を計算し、セクター上限を超えている場合に新規候補を除外。
    - calc_regime_multiplier(): market regime（bull/neutral/bear）に基づく投入資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes(): risk_based / equal / score に基づく発注株数決定ロジック、単元（lot_size）丸め、aggregate cap によるスケールダウン処理、cost_buffer による保守的見積り。
- Paper Trading 向けツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）を集計。
    - 基準値（稼働率 99%、成功率 90% など）に基づく PASS/FAIL 判定を出力。
    - DB パスは引数 --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。
- リサーチ（ファクター計算）モジュール（開発中）
  - research/factor_research.py: モメンタム、ボラティリティ、流動性、バリュー系ファクターを計算する方針で実装を開始。
    - DuckDB を用いた prices_daily / raw_financials への依存設計。
    - （注）ファイル末尾に未完の箇所が存在（実装継続が必要）。
- パッケージ情報
  - __init__.py によるバージョン定義 __version__ = "0.1.0" と主要サブパッケージ公開設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / Usage
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings._require() により未設定で起動時に例外を投げる想定。
- 実行例
  - 監視ループ起動: python -m kabusys.run_monitoring
  - Execution エンジン起動: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- Paper Trading と本番 DB の分離
  - run_execution は settings.is_paper に基づき PAPER_TRADING_SQLITE_PATH（data/paper_trading.db をデフォルト）を使用し、ペーパートレードで本番 DB を汚さない設計。
  - run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」との注記があり、監視用途の DB は本番 DB を指す実装になっている点に注意。
- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテーションで出力。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する。
- Kill / Stop フラグ
  - data/stop_requested.flag による外部停止指示に対応（両スクリプトで検知処理あり）。
  - KILL_FLAG_CLEAR_ON_START 環境変数で起動時の自動クリア動作を制御（validate_config は本番環境での設定ミスを警告する）。

Known issues / TODO
- research/factor_research.py は末尾で実装が切れている（未完）。完全なファクター計算の実装が必要。
- position_sizing.calc_position_sizes の price 欠損時のフォールバックについて TODO コメントあり（前日終値や取得原価を使う検討）。
- apply_sector_cap はセクターが "unknown" の場合に上限適用をスキップする設計だが、実運用での扱いに注意が必要。
- monitoring の DB 選定（環境に依らず本番 DB を使用する設計）が意図した挙動か要確認（運用ポリシーによっては変更が必要）。
- process_priority / cpu_affinity はプラットフォームや権限によって設定に失敗する場合があり、その際は警告でスキップする。

Contributing
- このリリースはコードベースから推測して作成した CHANGELOG です。実際のコミットログや意図した変更点と差異がある可能性があります。正確な履歴は実際の VCS コミットメッセージ・タグから生成することを推奨します。