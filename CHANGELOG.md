# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  

- 次のバージョンでは後方互換性がない変更を行う可能性があります。
- 日付はリリース日を表します。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開リリース。以降の機能はこのリポジトリの現行コードベースから推測してまとめています。

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定・ロード
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索して決定）。
  - OS 環境変数を上書きしない既定動作、.env.local による上書きサポート、KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化機能を実装（src/kabusys/config.py）。
  - 複雑な .env 構文対応（export プレフィックス、クォート内エスケープ、インラインコメントの扱いなど）。

- 設定管理 API
  - Settings クラスを追加し、環境変数から各種設定値を取得するプロパティを提供（J-Quants、kabuステーション、DB パス、paper_trading 用設定、監視閾値、実行環境フラグ等）。

- 対話式設定ウィザード CLI
  - python -m kabusys.config_setup で .env の初期作成・更新を対話式に支援（src/kabusys/config_setup.py）。
  - 生成される .env に機密トークンはマスク表示（ユーザーへの注意喚起あり）。
  - .env を Git にコミットしないようコメントで明記。

- 設定検証 CLI
  - python -m kabusys.validate_config による起動前チェックを追加（必須環境変数、KABUSYS_ENV の妥当性、DB パス存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）など）。
  - --strict オプションで警告も失敗扱いにできる。

- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。Paper Trading 時は MockBrokerClient を選択し、paper_trading 用 DB に分離して記録（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）（src/kabusys/run_monitoring.py）。
  - 両スクリプトとも最初にプロセス優先度を設定する仕組みを導入（set_process_priority を使用）。

- 実行時のプロセス制御ユーティリティ
  - set_process_priority / set_cpu_affinity を実装（Windows/Linux/macOS 等の差異を吸収、psutil を使用）。権限やプラットフォーム非対応時は警告してスキップ（src/kabusys/utils/process_priority.py）。

- Execution 系コンポーネント（呼び出し・組立て）
  - BrokerClientFactory によるブローカークライアントの抽象化（環境に応じて Mock/実ブローカーを切替）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てロジックを run_execution に実装（リスクパラメータのデフォルト設定を含む）。
  - ExecutionEngine は別スレッドで run_session を実行し、停止フラグで安全に停止可能。

- 監視・モニタリング基盤
  - Monitoring 用 DB 初期化処理を追加（init_monitoring_db を呼ぶことで冪等に監視テーブルを保証）。
  - run_monitoring で本番 sqlite_path を常に使用する設計（KABUSYS_ENV に依存しない監視データ記録）。

- ポートフォリオ構築ライブラリ
  - 候補選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
  - 重み計算: calc_equal_weights（等金額）/ calc_score_weights（スコア正規化、全スコアが 0 の場合は等分でフォールバック）。
  - セクター集中抑制: apply_sector_cap（既存保有比率が閾値超過セクターの新規候補を除外。unknown セクターは無視）。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に対応、未定義は 1.0 にフォールバック）。
  - 株数算出: calc_position_sizes（risk_based / equal / score の割当方式、lot_size 単位で切り捨て／スケール調整、aggregate cap と残差配分ロジックを実装）。

- リサーチ機能
  - ファクター計算モジュールを追加（DuckDB 接続を受け、prices_daily / raw_financials テーブルから Momentum / Volatility 等を計算する関数群）。calc_momentum / calc_volatility などの実装あり（src/kabusys/research/factor_research.py）。

- Paper Trading 検証ツール
  - tools/paper_verification_report: ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL 判定でレポート出力する CLI を追加。閾値はスクリプト内で定義（src/kabusys/tools/paper_verification_report.py）。

### Changed
- .env の読み込み順を明確化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護）。
- run_monitoring のポーリング間隔挙動
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下等）な場合はログで警告してデフォルト（60 秒）にフォールバック。

### Fixed
- run_execution / run_monitoring 停止処理の堅牢化
  - data/stop_requested.flag を検知して安全に停止する処理を追加。スレッド停止待ちや接続クローズを finally 節で保証。
- .env パーサの改善
  - クォート内のバックスラッシュエスケープ、インラインコメントの扱い、export プレフィックス等の処理を正しく実装して .env の誤解釈を減少。
- PAPER_FILL_MODE の入力値検証を追加（有効値: instant/partial/never/reject）。無効値は ValueError を発生させる。

### Security
- .env の生成スクリプトで「.env を絶対に Git にコミットしない」旨を明記（config_setup での出力ヘッダ）。
- 設定検証で必須機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定やプレースホルダ値をチェックして警告/エラーを出す。

### Documentation / UX
- CLI とスクリプトにヘルプ・使用例・注意書きを充実させています（各モジュールのトップドックストリングや CLI の説明）。
- config_setup の対話表示でシークレット値はマスク表示、既存値の再利用に対応。

### Notes / Migration
- 初回導入時の必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。設定がないと Settings の該当プロパティ参照で例外が発生します。
- .env を作成するには:
  - python -m kabusys.config_setup を実行し、続いて python -m kabusys.validate_config で検証することを推奨します。
- Paper Trading を使うには:
  - KABUSYS_ENV を paper_trading に設定すると、Paper Trading 用の専用 SQLite（デフォルト data/paper_trading.db）と Mock ブローカーが使用され、本番 DB と完全に分離されます。
- 実行・監視の停止:
  - プロジェクトルート/data/stop_requested.flag を作成すると run_execution/run_monitoring が安全に停止します。PID ファイルや kill フラグパスは Settings で設定可能です。
- DuckDB / SQLite のデータファイルパスは環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）で上書き可能です。config/ 配下の YAML は存在しない場合は警告になるため、必要に応じて生成スクリプト等で準備してください。

---

（この CHANGELOG はコードベースから実装の意図と動作を推測して作成しています。実際のリリースノート作成時はコミット履歴やプロジェクト管理システムの情報を参照して正確な差分を反映してください。）