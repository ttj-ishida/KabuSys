# Changelog

すべての注目すべき変更をここに記録します。慣例に従い Keep a Changelog 準拠の形式で記載します。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期リリースを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 実行用スクリプトを追加（起動エントリポイント）。
  - システム監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止はプロジェクト内の data/stop_requested.flag ファイルを検知して行う。
    - 監視用 DB は実行環境にかかわらず production の sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority を使用）。
    - check_once() 呼び出しの例外を捕捉してロギングし、ループ継続。
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。MockBrokerClient の利用を想定（broker_factory 経由）。
    - エンジンは別スレッドで実行され、停止フラグで安全に停止できる。
    - PID ファイルパスや停止フラグの動作をサポート。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理・自動ロード機能を追加（src/kabusys/config.py）。
  - .env ファイル（プロジェクトルートの .env/.env.local）を自動で読み込む（OS 環境変数が優先）。
  - _find_project_root() により .git または pyproject.toml を基準にプロジェクトルートを自動検出するため、CWD に依存しない実装。
  - .env のパースは引用符、エスケープ、インラインコメントを考慮した堅牢なパーサーを実装。
  - 多数の設定プロパティを提供（J-Quants, kabuステーション, LINE, DuckDB/SQLite パス、監視閾値、環境判定プロパティ等）。
  - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等をサポート。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD が利用可能。
- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
  - 対話式に .env を作成・更新する機能。既存値の読み込み・マスク表示、選択肢サポート、保存確認あり。
  - .env 書き出しテンプレートを提供（機密値は明示的に扱うよう注記）。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）を検査。
  - --strict オプションで警告を FAIL 扱いにできる。
  - 本番（live）向けの追加ガード（LINE 通知設定のチェック、KILL_FLAG_CLEAR_ON_START の警告）を実装。
- Paper Trading 用検証レポートスクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - SQLite（paper_trading）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して人間向けレポートを出力。
  - デフォルト閾値（稼働率、成功率、送信率、P95 レイテンシ）に基づく PASS/FAIL 判定を出力。
  - --from / --to / --db オプションをサポート。
- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/*）。
  - 候補選定と重み計算（portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択。タイブレークに signal_rank を採用。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター時価を計算して上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - 銘柄ごとの株数決定・資金配分・丸め処理（position_sizing.py）
    - allocation_method="risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）での丸め、1 銘柄上限、aggregate cap（available_cash）を超える場合はスケールダウンし、残差分を lot 単位で再配分するアルゴリズムを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積りによるスケーリング。
- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。
  - set_process_priority("high" | "normal" | "low")、set_cpu_affinity(N) を提供。
  - 権限不足や未サポート環境時は警告を出して安全にスキップ。
- リサーチ用ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
  - prices_daily / raw_financials を参照して Momentum / Volatility / Liquidity / Value 系ファクターを計算する設計（DuckDB 接続を受け取る）。
  - calc_momentum, calc_volatility 等の実装を含む（長期 MA や ATR などの定義付き）。
- package exports を整備（src/kabusys/portfolio/__init__.py, src/kabusys/tools/__init__.py）。
- その他ユーティリティや小さなモジュールを追加（order/risk/execution 等への入口を想定した import 構成）。

### Changed
- （初回リリース）パッケージ全体の設定と挙動を整理:
  - .env の自動ロード順は OS 環境変数 > .env.local > .env（OS 環境変数の保護を考慮）。
  - 監視・実行のスクリプトは起動時にプロセス優先度を設定して安定稼働を優先。
  - Paper Trading 環境は本番 DB と完全分離されることを明示（paper_sqlite_path）。

### Fixed / Reliability improvements
- .env パーサーを堅牢化（引用符・エスケープ・インラインコメント対応）して誤読を低減（src/kabusys/config.py）。
- MONITOR_POLL_INTERVAL の値検証を追加。0 や負の値、非整数が与えられた場合はデフォルト（60秒）にフォールバックして警告を出力（src/kabusys/run_monitoring.py）。
- DB 初期化処理を冪等化（monitoring テーブルの初期化は複数回呼んでも安全）（run_monitoring/run_execution で init_monitoring_db を呼出し）。
- 監視ループ内での check_once() 実行時に例外が発生してもループを継続し、例外情報をロギングすることで単発障害での永久停止を防止。
- process_priority の OS 非対応や権限不足時の挙動を警告ログにしてスキップすることで起動失敗を防止。

### Notes / Documentation
- .env ファイルは絶対にリポジトリにコミットしないことを明記（config_setup のテンプレートコメント）。
- config_setup 実行後は validate_config による検証を推奨するメッセージを追加。
- Paper Trading 検証レポートはデータが無い場合に N/A 表示・FAIL 条件を明示する設計。

---

今後の予定（例）
- strategy / execution の各コンポーネント（Engine の細部、broker 実装、order manager 等）の詳細実装・テスト追加。
- ファクター・ポートフォリオ計算の単体テストと性能最適化。
- ドキュメント（README、運用手順）の整備と運用向け安全弁（監視アラート、リトライ）強化。

もし追加で特定ファイルの差分や変更履歴（例えば各関数の詳細な変更点）をより厳密に反映したい場合は、対象ファイルや変更前の状態を教えてください。