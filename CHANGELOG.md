CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載します。  
慣例に従い主なカテゴリを分けています（Added / Changed / Fixed / その他）。日付はリリース日を示します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース: KabuSys コア機能を実装。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB（デフォルト: data/paper_trading.db）と MockBrokerClient を使用する分離設計を採用。PID ファイル管理、停止フラグ（data/stop_requested.flag）検出による安全停止に対応。
  - run_monitoring: SystemMonitor を定期ポーリングする監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を参照して動作する設計。
- 設定管理
  - config.py: .env 自動ロード機能（.env, .env.local の読み込み、OS 環境変数優先）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止をサポート。細かい .env パース（export 形式、クォート文字列、エスケープ、インラインコメント処理）を実装。Settings クラスで各種設定プロパティ（DB パス、API トークン、環境判定、閾値等）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。既存値のマスク表示や確認プロンプト、.env 書き出しを実装。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性検査、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検査（PyYAML 任意）を実行）。--strict モードを追加（警告をエラー扱い）。
- ポートフォリオ構成
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）・等金額/スコア加重の重み計算を追加。スコア合計が 0 の場合は等分にフォールバックする警告を実装。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。allocation_method として "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウンと端数配分ロジック、コストバッファ考慮を実装。
- 実行関連コンポーネント（骨格）
  - 実行系モジュール（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager）への接続と起動フローを run_execution で組み立てる実装（詳細ロジックは外部ファイルに委譲）。
- 監視関連
  - monitoring_db の初期化ユーティリティ（init_monitoring_db）と SystemMonitor 連携。監視ループで例外を捕捉してログに残しつつ継続する堅牢化。
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定する。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続するフォールバックを実装。ログレベル・ログディレクトリの解決順を導入。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux, macOS 等）差分を吸収し psutil を利用して優先度を設定。アクセス権限エラー等は警告ログで無害にスキップ。set_cpu_affinity も提供。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出し PASS/FAIL 判定を出力。期間指定 (--from/--to) と DB パス指定 (--db) をサポート。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨格（モメンタム等の計算方針、期間定義、DuckDB 参照による計算を想定）を追加（モジュールは継続実装中）。

Changed
- ログ出力設計: 標準エラーではなく標準出力（stdout）へ StreamHandler を出力するように変更（cron / Task Scheduler などで stdout/stderr を一本化する運用を想定）。
- 実行開始時にプロセス優先度を "high" に設定するよう起動スクリプト（run_execution、run_monitoring）で統一。
- run_execution は Paper Trading 時に paper 用 SQLite を自動選択して本番 DB と分離する動作を明確化。

Fixed / Robustness
- MONITOR_POLL_INTERVAL のパースで不正値（0 以下や非数）が与えられた場合にデフォルトへフォールバックし、警告ログを出すように堅牢化（time.sleep に不正な値を渡す事故を防止）。
- .env パーサの強化: export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等を正しく処理するよう改良。
- ログディレクトリ作成失敗時のフォールバック（ファイルハンドラ作成失敗をログに残しつつコンソールのみで継続）を実装し、起動時に致命的にならないようにした。

Security / Privacy
- config_setup の確認表示でシークレット値（トークン・パスワード）はマスク表示（****）するよう実装。

Notes / Known limitations
- research/factor_research.py は実装途中（モメンタム計算部分の実装継続が想定される）。DuckDB スキーマ（prices_daily / raw_financials 等）に依存するため、該当テーブルが整備されている環境での利用を想定。
- 実際の発注・ブローカー連携ロジックは BrokerClientFactory / ExecutionEngine 等へ委譲しており、本リリースでは骨格と接続フローを提供。各コンポーネントの細部実装は別途。
- 単元株サイズ（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄毎の単元マスタへの対応を予定。

メンテナンス
- バージョンはパッケージ __version__ にて "0.1.0" を設定。

以上。今後のリリースでは実装完了したファクター計算、追加の QA / テスト、より詳細なドキュメント（API 仕様・設定例・運用手順）について追記予定です。必要であれば、この CHANGELOG を英語版に変換するか、各項目をさらに細分化して PR 単位の履歴に分けることもできます。どの形式をご希望か教えてください。