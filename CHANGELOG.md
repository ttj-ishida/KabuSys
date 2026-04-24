# Changelog

すべての重要な変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
※以下は提供されたソースコードから推測して作成した変更履歴です。

---

## [0.1.0] - 2026-04-24

### Added
- 全体
  - パッケージ初期リリース相当の主要コンポーネントを追加。
  - バージョンは `kabusys.__version__ = "0.1.0"`。

- 設定 / 起動
  - Settings クラスを実装し、環境変数経由で各種設定（API トークン、DB パス、動作環境、しきい値等）を提供。
  - プロジェクトルートの `.env` / `.env.local` を自動読み込みする仕組みを追加（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - `.env` ファイルのパースを堅牢化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどに対応）。

- CLI / ツール
  - `python -m kabusys.config_setup`：対話式の環境設定ウィザードを追加（.env の初期作成・更新を支援）。
  - `python -m kabusys.validate_config`：起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在/パースチェック（PyYAML があればパースも実施）を行う。`--strict` モードをサポート（警告をエラー扱いにする）。
  - `python -m kabusys.tools.paper_verification_report`：Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）による PASS/FAIL 判定を実行。

- 実行系 / 監視
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite を使用して本番 DB と分離（`PAPER_TRADING_SQLITE_PATH`）。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する設計。
  - 停止制御用にプロジェクトの `data/stop_requested.flag` を用いる仕組みを導入（フラグ検知でループ停止）。

- DB / 分析
  - DuckDB と SQLite の両方を想定した初期接続処理を追加（`Settings.duckdb_path` / `Settings.sqlite_path`）。
  - 監視テーブルの初期化関数を呼び出すことで冪等に監視用テーブルを保証（`init_monitoring_db` を利用）。

- ロギング / プロセス制御
  - `kabusys.utils.logging_setup.setup_logging` を追加。ルートロガーに stdout 出力（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。ログレベルとログディレクトリの解決ルールを実装。
  - `kabusys.utils.process_priority` を追加。Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを提供。CPU affinity 固定機能も実装（権限不足時は安全にスキップ・警告）。

- ポートフォリオ構築 / リスク管理
  - `kabusys.portfolio.portfolio_builder`：シグナル候補選定（スコア順）、等分配・スコア加重配分ロジックを追加。スコア全0時のフォールバック挙動を定義。
  - `kabusys.portfolio.risk_adjustment`：セクター集中防止（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - `kabusys.portfolio.position_sizing`：発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、1 銘柄上限、利用可能現金に対する aggregate スケーリング、cost_buffer を用いた保守的見積りなどをサポート。

- 研究用ファクター計算
  - `kabusys.research.factor_research`：モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、バリュー（PER/ROE）、流動性等の計算を行うモジュールを追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。

### Changed
- ログ出力は標準エラーではなく標準出力（stdout）に出すポリシーを採用（cron / Scheduler での取り扱いを考慮）。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ続行する堅牢化を実施。
- プロセス優先度設定・CPU affinity は権限不足や未対応 OS の場合に安全にスキップし、詳細をログに残すように変更（例: AccessDenied, NotImplementedError をハンドリング）。

### Fixed
- 環境変数パースの不備対策を導入：クォート内のバックスラッシュエスケープ処理、export プレフィックス、インラインコメント判定の改善により .env の誤読を低減。
- 環境変数 MONITOR_POLL_INTERVAL の不正値（負値・非整数など）に対しデフォルトにフォールバックし、警告ログを出すように修正。
- `validate_config` が PyYAML 非インストール環境でも動作するように、YAML 検査をオプション化（未インストール時は警告を出してスキップ）。

### Notes / Known issues / TODO
- risk_adjustment.apply_sector_cap 内に価格欠損時の扱いに関する TODO が残る（価格欠損時にエクスポージャーが過少見積りされる可能性）。将来的に前日終値や取得原価等でのフォールバックを検討する旨の注記がある。
- position_sizing: lot_size を全銘柄共通としている。将来的には銘柄毎の lot_map を受け取る拡張が想定されている（TODO コメントあり）。
- research.factor_research は設計方針・定数やモメンタム計算等を実装しているが、実際の SQL や全関数実装の詳細は今後整備される可能性がある（提供コードは一部を含む）。
- ExecutionEngine の動作や BrokerClientFactory の実装（Mock / 実ブローカの具象）の挙動は本ログに含まれないため、実運用前に接続先設定・モックの確認が必要。
- 一部の操作（プロセス優先度設定、CPU affinity、ログファイル作成）は OS 権限や環境に依存するため、権限不足時は安全にフォールバックする設計になっているが、期待通りに動作しないケースがある点に注意。

---

今後のリリースでは、テストカバレッジの拡充、ドキュメント（API・運用手順）の追加、銘柄別 lot_size 対応、価格欠損時フォールバックロジックの実装、research モジュールの完遂などが考えられます。必要であれば、この CHANGELOG をベースに Unreleased 項目を追加・分割して更新案を作成します。