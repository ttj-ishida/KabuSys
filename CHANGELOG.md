CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース (バージョン 0.1.0)。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動・監視。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にシャットダウン。
    - 実行 PID を data/execution.pid に記録する仕組み（pid_file を使用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了し、例外発生時はログを出して次ポーリングへ継続。
- 設定関連
  - config.py: .env 自動読み込み（.env / .env.local）と堅牢な .env 行パーサ (.env の export 形式、クォート、インラインコメントなどに対応) を実装。
    - 環境変数取得用 Settings クラスを提供（J-Quants / kabu API / DB パス / ペーパートレード設定 / 監視閾値 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加（CLI）。
    - デフォルト値、シークレット扱い、説明付きの質問群を用意し .env を生成。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV 値、DB パス、config/*.yaml の存在・パース検証（PyYAML が無ければ警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等重・スコア重み）を追加。
  - portfolio/risk_adjustment.py: セクター集中上限の適用と市場レジームに応じた乗数計算を追加。
  - portfolio/position_sizing.py: 株数決定ロジックを追加（risk_based, equal, score の各方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 反映）。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート (TimedRotatingFileHandler) を root ロガーに設定、デフォルト logs/ ディレクトリ、30日バックアップ。
    - ログレベル・ログディレクトリは引数・環境変数から解決。ディレクトリ作成に失敗した場合はファイル出力をスキップして console のみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収し、アクセス権限不足などで失敗しても警告ログを出して安全にスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を提供（未指定なら変更なし）。
- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出して監視用テーブル存在を保証（冪等）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計。
    - PASS/FAIL の閾値（稼働率 99%、注文成功率 90% 等）を定義して判定を出力。
    - --from/--to/--db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先。
- 研究モジュール（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum/Value/Volatility/Liquidity の設計記述、DuckDB 接続想定）。
- パッケージ初期化
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- -（初回リリースのため該当なし）

Fixed
- -（初回リリースのため該当なし）

Deprecated
- -（初回リリースのため該当なし）

Removed
- -（初回リリースのため該当なし）

Security
- -（初回リリースのため該当なし）

Notes / Known limitations
- run_monitoring は説明どおり「監視用」プロセスであり、MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）が与えられた場合はデフォルト 60 秒にフォールバックしてログ警告を出します。
- run_execution は paper_trading モード時に本番 DB とは完全に分離された paper_trading 用 SQLite を使用します。実運用時の誤接続を避けるため .env の設定を必ず確認してください（validate_config の利用を推奨）。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に安全にスキップし、警告ログを出力します。
- portfolio.position_sizing の価格欠損時の挙動や lot_size の将来的拡張について TODO コメントがあります（現状は全銘柄共通の単元を想定）。
- research.factor_research.py はモジュール骨格と設計方針を実装済みですが、ファイル末尾に未完の実装（calc_momentum の続き）が含まれている可能性があります。研究機能は今後のリリースで完成させます。

作者注
- 本 CHANGELOG はリポジトリ内のソースコードから機能追加・設計意図・コメントを推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。