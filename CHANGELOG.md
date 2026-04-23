CHANGELOG
=========
このプロジェクトは「Keep a Changelog」仕様に準拠して変更履歴を記録します。
日付は YYYY-MM-DD 形式で記載しています。

[Unreleased]
-------------

- （現在のコードベースでは未リリースの変更はありません）

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
  - 実行エントリポイント
    - run_execution.py：ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db）に完全分離して記録する仕組みを備える。停止フラグ（data/stop_requested.flag）と PID 管理をサポート。
    - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能。監視は環境にかかわらず本番の sqlite_path を参照する設計。停止フラグ検知で安全にループ終了。
  - 設定関連
    - config.py：環境変数・設定管理（Settings クラス）を実装。.env 自動読み込み（.env.local に上書き可能）と OS 環境変数保護をサポート。多くの設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、paper_trading 関連、監視閾値等）を提供。
    - config_setup.py：.env を対話的に作成・更新するウィザード CLI を追加。機密項目はマスク表示、デフォルトや選択肢を提示して保存可能。
    - validate_config.py：起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検査（PyYAML 利用）などを実行。--strict オプションで警告を FAIL 扱いにできる。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py：StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定するユーティリティを追加。ログディレクトリ自動作成、設定済みハンドラのクリア、ログレベル解決順を実装。
    - utils/process_priority.py：psutil ベースで Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加。アクセス権限不足等のフォールバック処理あり。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py：候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全0 の場合は警告を出して等配分にフォールバック。
    - portfolio/risk_adjustment.py：セクター集中上限を適用する apply_sector_cap、および市況レジームに応じた資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバックで 1.0。
    - portfolio/position_sizing.py：allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出ロジックを実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer による保守的見積り、残差を考慮した追加配分ロジックを備える。
    - package-level export を整備（kabusys.portfolio）。
  - 研究・ツール
    - research/factor_research.py：DuckDB 接続を受け取りモメンタム等のファクターを計算するための枠組みを追加（モメンタム等の計算仕様、スキャン幅定義を含む）。（実装は継続中の箇所あり）
    - tools/paper_verification_report.py：Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、PASS/FAIL 判定を出力する。閾値は定数で定義（稼働率>=99% 等）。
  - データベース関連
    - monitoring/monitoring_db.py への初期化呼び出し（init_monitoring_db）を各起動スクリプトで実行し、監視テーブル存在を保証（冪等）。
    - DuckDB と SQLite を併用する設計を導入（duckdb は分析用、sqlite は監視/履歴用）。
  - バージョン情報
    - __init__.py に __version__ = "0.1.0" を設定。

Changed
- 環境変数読み込みの仕様を明確化
  - 自動 .env ロード順序を OS 環境 > .env.local > .env として実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 読み込み時に OS 環境変数を保護（既存の OS 環境変数は上書きされないように protected set を使用）。
- ログ出力の扱いを統一
  - コンソール出力は stdout を使用（stderr ではない）ため、外部スケジューラからのリダイレクトが容易。
  - 既存ハンドラは再設定時に flush/close してから削除することで二重出力を防止。

Fixed
- .env パーサの強化
  - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢なパースを実装。
  - 無効行や空行、コメント行を適切に無視するよう修正。
- 設定検証の堅牢化
  - config/*.yaml のパースチェックは PyYAML 未インストール時にスキップし、警告を出すように修正。
  - DB パスの親ディレクトリが存在しない場合に警告を出す（起動時に自動作成される可能性に言及）。

Security
- 設定ウィザードで機密値（トークンやパスワード）をマスク表示するように変更。
- .env 作成時に「絶対に Git にコミットしないこと」を明示するヘッダを追加。

Notes / Usage
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 設定ウィザード:
  - python -m kabusys.config_setup
- 実行:
  - 監視: python -m kabusys.run_monitoring
  - 発注エンジン: python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Deprecated
- なし。

Removed
- なし。

Security
- 重大なセキュリティ問題は現時点で報告されていません。機密情報は .env に保存し、リポジトリにコミットしないでください。

----

注: 上記はコードベースの内容から推測して作成した CHANGELOG です。リリース日や一部の実装詳細（内部の関数実装進捗等）はソース中のコメントや現行コードに基づく推定です。実際の開発履歴やコミット履歴に基づく正式な CHANGELOG はプロジェクトのバージョン管理履歴を参照して作成してください。