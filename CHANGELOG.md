# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

（今後の変更をここに記載）

## [0.1.0] - 2026-04-18

Added
- 初回リリース。KabuSys のコア機能群を追加。
- エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用し、本番 DB と分離して MockBroker を利用する動作を実装。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用して安全に停止可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に依らず本番の sqlite_path を使用する挙動を明示。
- 設定管理・初期化
  - config.py: 環境変数読み込み・設定取得ユーティリティを追加。.env/.env.local の自動ロード（プロジェクトルート検出ロジック付き）、保護された OS 環境変数を上書きしないロード、必須 env の検証メソッドを追加。PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等のプロパティを実装。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加（秘密値マスク、既存値の再利用、保存確認等）。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検査する CLI を追加。--strict オプションで警告も失敗扱いにできる。live 環境向けの追加チェック（LINE トークンや Kill Switch 設定）を実装。
- 監視・初期化サポート
  - monitoring.monitoring_db: 監視用 DB 初期化関数（init_monitoring_db）を利用して起動時に監視テーブルの存在を保証。
  - run_monitoring / run_execution で sqlite3/duckdb 接続を確立し、終了時に必ずクローズするよう実装。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: アプリケーション共通のロギング設定を追加。stdout 出力（StreamHandler）と日次ローテーションによるファイル出力（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフェイルセーフを実装。
  - utils/process_priority.py: Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS では警告してスキップする安全策を採用。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を追加。スコア全てが 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限適用 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を追加。未知レジームはフォールバックして 1.0 を返す挙動を実装。
  - portfolio/position_sizing.py: 発注株数算出ロジックを追加。risk_based / equal / score の配分方式をサポート、単元株（lot_size）丸め、1銘柄上限・総投下上限、cost_buffer を考慮した保守的見積り、合計コスト超過時のスケールダウン（残差配分による再割当）を実装。
  - portfolio/__init__.py: 上記機能を公開 API としてエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（P95）等を計算し PASS/FAIL を判定。閾値（稼働率 99%、成功率 90% 等）を定義。CLI で --from / --to / --db を指定可能。
- 研究用ファクター計算（部分実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム等の設計と一部定数を実装）。（実装は継続中。一部コードはファイル末尾で切れている）

Changed
- なし（初回構成のため）

Fixed
- なし（初回構成のため）

Security
- 秘密値（トークン/パスワード）は config_setup の出力でマスクされるなど、取り扱いに配慮した設計。

Notes / 動作上の注意
- run_monitoring は監視 DB に対して本番の sqlite_path を利用することを意図しているため、環境にかかわらず monitoring 用 DB を参照する点に注意。
- run_execution は paper_trading モードで paper_sqlite_path を使用するなど、本番 DB とデータ分離が図られている。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出できない場合はスキップされる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- process_priority / set_cpu_affinity は権限や OS により完全に反映されない場合がある。失敗時は警告ログを出力してスキップする。
- ロギングでログディレクトリ作成に失敗するとファイル出力は無効化され、標準出力のみで動作する（デフォルトは logs/<app_name>.log）。

----

今後の予定（例）
- research/factor_research の完全実装（各ファクター計算の SQL 実装、Z スコア正規化との統合）
- テストカバレッジの拡充、CI の導入
- strategy / execution の追加実装およびドキュメント拡充

<!--
参考:
- リリース日付は現時点（2026-04-18）を記載しています。必要に応じて変更してください。
- ここに記載した項目はコードベースから推測してまとめたものであり、実際の変更履歴やコミットメッセージと完全一致するわけではありません。
-->