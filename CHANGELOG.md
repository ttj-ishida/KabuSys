# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って管理します。  
稼働中のコードベースから推測した初期リリースの変更点を日本語で記載しています（実ファイルの差分履歴がないため、コードの構造・コメントから機能追加や設計方針を要約しています）。

全般
- バージョンはパッケージメタデータで __version__ = "0.1.0" が設定されています。
- デフォルトのログディレクトリは `logs/`、ログは日次ローテーション（30日分保持）で保存されます。
- 環境変数は .env/.env.local を自動ロードする仕組みを備え、OS 環境変数を保護する（上書きを制御）実装になっています。
- DuckDB と SQLite を併用する設計。分析用に DuckDB、監視・トレード履歴用に SQLite を想定。

[Unreleased]
- （現状なし）

[0.1.0] - 2026-04-19
========================================
Added
- 起動スクリプト / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト配下の `data/stop_requested.flag` ファイルで検知する。監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は Mock（ペーパー）ブローカを利用し、paper_trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）へ記録して本番 DB と分離する。実行中の停止は `data/stop_requested.flag` で検知、PID ファイル管理のため `data/execution.pid` を利用。

- 設定・環境系
  - config.py: 環境変数/設定管理クラス `Settings` を追加。多くの設定項目（J-Quants、kabuAPI、LINE、DB パス、監視閾値、環境フラグなど）をプロパティとして提供。自動 .env ロード機能（.env → .env.local、OS 環境を保護）を実装。`PAPER_FILL_MODE` 等の検証ロジックも含む。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加（`python -m kabusys.config_setup`）。シークレット項目はマスク表示し、書き込み前の確認を行う。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検査する CLI を追加（`--strict` オプションで警告を FAIL 扱いにできる）。YAML パーサが存在しない場合はそれを検出して警告する。

- ロギング・プロセス制御
  - utils/logging_setup.py: 共通ログ初期化ユーティリティを追加。StreamHandler（stdout）＋TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定し、既存ハンドラの重複設定を防止する。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを追加。アクセス権限や未対応 OS に対しては安全にフォールバックして警告を出力する。

- ポートフォリオ構築モジュール（純関数，テスト容易）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（score/equal）を提供。スコアが全て 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限の適用関数と市場レジームに応じた投下資金乗数（regime multiplier）を追加。未知のレジームはフォールバック（1.0）して警告。
  - portfolio/position_sizing.py: 単銘柄・集計キャップ・ロット丸め・リスクベース配分等を含む株数算出ロジックを実装。allocation_method として `"risk_based"`, `"equal"`, `"score"` をサポートし、コストバッファ (slippage/fee) を考慮したスケーリング処理を行う。

- 実行系コンポーネント（起動スクリプトから組み立て）
  - ExecutionEngine 周辺（BrokerFactory、OrderManager、OrderRepository、Reconciler、RiskManager 等）の組み立て処理を run_execution で実装。RiskConfig にデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期化時にブローカーから利用可能現金を取得してリスク管理に利用する。

- 監視 DB 初期化 / DuckDB 統合
  - monitoring_db の初期化を行うユーティリティを呼び出して、起動時に監視テーブルの存在を保証（冪等）。DuckDB は分析・研究用に接続される（paths は Settings で管理）。

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。稼働率・注文成功率/送信率・リスク却下数・API レイテンシ（平均／最大／P95）を算出し PASS/FAIL 判定を出力する。P95 算出、日付フィルタ（ISO8601 UTC への変換）、DB 存在チェック、しきい値はコード内定義（稼働率 99%、等）で行う。

- 研究用スケルトン
  - research/factor_research.py: ファクター計算モジュールの骨子を追加。Momentum/Value/Volatility/Liquidity 等を計算する方針と定数群を定義（各種窓長、スキャン範囲等）。関数 calc_momentum の冒頭実装が存在（実装途中の可能性あり）。

Changed
- なし（初回リリース相当のため、既存からの変更記録はなし）。  
  （ただしログやプロセス優先度設定は各起動スクリプト冒頭で必ず実行される設計に統一されています。）

Fixed
- 環境変数ロードの堅牢化
  - .env のパースはクォート内のエスケープやインラインコメントに対応。`export KEY=val` 形式にも対応しており、自動ロード時に OS 環境変数を保護する実装となっている。
- ロギング設定の耐障害化
  - ログディレクトリ作成失敗時にファイルハンドラの作成をスキップして、コンソール出力のみで継続するように改善。

Security
- なし特記。シークレット値（トークンやパスワード）は Settings を通じて必須チェックされた上で .env に保存される（config_setup はシークレット項目をマスク表示）。

Deprecated
- なし

Removed
- なし

Notes / 設計上の重要事項（ドキュメント的注意）
- run_monitoring は意図的に「環境にかかわらず」本番 sqlite_path を使用する実装になっている（コメントおよびコードに明示）。ローカル開発で監視を別 DB に分離したい場合は設定またはコードの変更が必要。
- run_execution は paper_trading 環境向けに DB を分離する設計（Settings.paper_sqlite_path を利用）。ペーパートレードと本番のデータ混在を防ぐ意図。
- process_priority 系は権限に依存する操作（nice や優先度設定）を行うため、実行環境の権限不足時には警告を出してスキップする安全設計になっている。
- portfolio/position_sizing のスケーリングロジックはロット単位（lot_size、デフォルト 100）で丸めを行うため、個別銘柄で単元が異なる場合は将来的に拡張が必要（TODO コメントあり）。
- research/factor_research の実装は途中の可能性があり、完全なファクター計算は未完成（calc_momentum 実装の途中でファイル終端が切れている）。

========================================

（注）本 CHANGELOG は提供されたソースコードの構造・コメントから機能追加と設計方針を推測して作成したもので、実際のコミット履歴を基にしたものではありません。必要であれば、実コミットログやリリース毎の差分に合わせて更新版を作成します。