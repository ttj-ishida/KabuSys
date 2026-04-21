Keep a Changelog に準拠した形式で、このコードベースから推測できる変更履歴（CHANGELOG.md）を日本語で作成しました。

注意:
- 実際のコミット履歴が無いため、コードの実装内容から推測して機能追加・動作仕様を記載しています。
- バージョン情報はパッケージ定義（src/kabusys/__init__.py の __version__）に基づき v0.1.0 を初回リリースとして扱い、日付は本日（2026-04-21）を付与しています。

CHANGELOG.md
=============
全体方針:
- 重要な変更・追加機能・修正点を「Added / Changed / Fixed / Security / Deprecated / Removed」に分類して記載しています。
- 新規リリース (0.1.0) に実装されている主要な機能を中心にまとめています。

Unreleased
----------
（現在のところ未リリースの差分はありません）

[0.1.0] - 2026-04-21
-------------------
Added
- 基本アプリケーション構成を初期リリースとして追加。
  - パッケージ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
- 環境設定・読み込み機能を追加（src/kabusys/config.py）。
  - .env/.env.local からの自動読み込み機構を備え、プロジェクトルートの検出は .git または pyproject.toml を基準に行う（CWD に依存しない）。
  - .env のパース機能を強化（export プレフィックス対応、クォート文字列のエスケープ、インラインコメントの扱いなど）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスで環境変数をラップし、各種設定値（DBパス、API トークン、KABUSYS_ENV、ログレベル、しきい値等）を型変換・検証して提供。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper-trading 用設定を用意。
- 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
  - .env を対話的に作成・更新するウィザードを提供。既存値の再利用、秘密値のマスク表示、ファイル書き込みをサポート。
  - 出力される .env には注意書きを付与（.env をコミットしないよう明記）。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。
  - --strict モードで警告を fail 扱いにできる。
  - 本番環境向けの追補チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定）を実施。
- 実行系エントリスクリプトを追加。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH 対応）。
    - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - stop フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。スレッドでエンジンを実行し、停止フラグ検知時に安全停止を行う。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告しデフォルトにフォールバック。
    - 起動時にプロセス優先度を High に設定。
    - 監視用 DB は環境に依らず本番 sqlite_path を参照して初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。例外時はログを残して次ポーリングまで待機。
- ロギングユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を構成する setup_logging() を提供。
  - ログレベル・ログディレクトリ解決の優先順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX の差分を吸収して set_process_priority(level) / set_cpu_affinity(count) を提供。アクセス拒否等は警告でスキップ。
- ペーパートレード検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - PAPER_TRADING_SQLITE_PATH を指定して、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を集計・表示。
  - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL を判定。
  - CLI オプションで期間指定（--from / --to）および DB パス指定（--db）をサポート。
- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）。
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。全てメモリ内計算（DB参照なし）。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジームは警告してフォールバック。
  - position_sizing: 株数決定ロジック（calc_position_sizes）。risk_based / equal / score の配分方式、単元株丸め（lot_size）、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer による保守見積り等を実装。
- リサーチ（ファクター計算）モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
  - Momentum / Value / Volatility / Liquidity の計算方針と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（モジュール途中実装あり）。

Changed
- ログの標準出力は stderr ではなく stdout を使用するように設計（cron / Task Scheduler でのリダイレクトを想定）。
- .env 読み込み順序を明確化: OS 環境 > .env.local > .env。既に OS にある環境変数は保護される。

Fixed
- 環境変数パースの強化により、クォート文字列・エスケープ・インラインコメントなどの不正解釈を回避。
- 起動時の DB 初期化処理（監視テーブルの冪等初期化）を run_execution/run_monitoring 側で保証。

Security
- .env ファイルに関する注意喚起をウィザードおよびテンプレートに明記（.env を Git にコミットしないこと）。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Internal / Notes
- 一部モジュールは将来の拡張を意識した TODO コメントを含む:
  - position_sizing: 将来的な銘柄別 lot_size 対応を想定。
  - risk_adjustment.apply_sector_cap: 価格が欠損した場合のフォールバック価格ロジックは未実装（TODO）。
- validate_config は PyYAML 未導入環境でも実行できるように警告を出して YAML 検証をスキップする実装。
- process_priority と CPU affinity 設定はアクセス権限や未対応プラットフォームで失敗した場合に処理を続行するよう堅牢化されている。

今後の提案（非必須）
- リリース毎に自動生成される CHANGES を用意するため、コミットメッセージや tag に基づく changelog 自動化の導入を検討してください（例: github の Release note 自動化）。
- factor_research の完全実装、ユニットテスト、CI の導入により品質を強化してください。
- セキュリティ観点で .env のサンプル(.env.example) に機密情報を残さない運用ルールの徹底を推奨します。

--- 
この CHANGELOG はソースコードから推定して作成したため、実際の履歴（コミット単位）と若干の差異がある可能性があります。必要であれば実際の git 履歴やリリースノートに合わせて調整します。