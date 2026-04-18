CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in
Japanese. — https://keepachangelog.com/ja/1.0.0/

フォーマット
------------
- バージョン見出しは [version] - YYYY-MM-DD の形式を使用しています。
- セクション: Added, Changed, Fixed, Deprecated, Removed, Security

[0.1.0] - 2026-04-18
-------------------

Added
-----
- 基本アプリケーション構成およびコアユーティリティを実装。
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプトを追加:
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアントの抽象化。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による安全停止をサポート。
    - エンジンの PID を data/execution.pid に書き出す仕組み（設定ファイル経由でパス指定可能）。
  - run_monitoring: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視モジュールは KABUSYS_ENV に関わらず本番用 sqlite_path を使用（監視データは共通 DB に保存）。
    - stop flag（data/stop_requested.flag）検知、KeyboardInterrupt のハンドリング、例外ログ出力で安全に動作継続。
- 設定管理:
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み機能（プロジェクトルートが特定できる場合のみ）。
    - 環境変数の検証・取得ユーティリティ（必須値チェック _require）。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID/kill flag パス、閾値等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定支援ツール:
  - config_setup: 対話式ウィザードで .env を生成／更新する CLI（src/kabusys/config_setup.py）。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用に対応。
    - デフォルト項目群を定義し .env を生成。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML が無ければ警告）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ:
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30日保持）を設定するユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - LOG_DIR/LOG_LEVEL の解決順をサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - process_priority: Windows/Linux/macOS を透過してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - psutil を用いて実装。権限不足や未対応 OS の場合は警告を出してフォールバック。
- ポートフォリオ構築モジュール（純関数で DB 参照なし）:
  - portfolio_builder: 候補選定（select_candidates）、等金額/スコア加重配分（calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の配分方法対応、単元株（lot_size）丸め、aggregate cap（利用可能現金でスケールダウン）等を実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- 研究用モジュール:
  - factor_research: DuckDB 接続を受け取ってモメンタム等のファクターを計算するためのモジュール骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム/MA/ATR/出来高系の計算方針と定数を定義。
- ペーパートレード検証レポート:
  - tools/paper_verification_report: SQLite（Paper Trading DB）から統計を取り、PASS/FAIL 判定のレポートを生成するスクリプトを追加。
    - 指標: 稼働率(>=99%)、注文成功率(>=90%)、送信率(>=95%)、P95レイテンシ(<=200ms)。
    - 日付フィルタ、P95 算出、欠損テーブルに対するフォールバックを実装。
    - DB パスは --db, 環境変数 PAPER_TRADING_SQLITE_PATH, デフォルト の優先順で解決。
- 監視 DB 初期化ユーティリティを各起動スクリプトから呼び出し（init_monitoring_db）。

Changed
-------
- なし（初回リリース）

Fixed
-----
- なし（初回リリース）

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- なし

Known issues / Notes
-------------------
- src/kabusys/research/factor_research.py の calc_momentum 実装はファイル末尾が途切れており未完の箇所があります（実装継続予定）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を見つけられない場合はスキップします。CI/特殊配置では明示的に環境変数を設定してください。
- validate_config の YAML 検証は PyYAML 未インストール時にスキップされ、警告が出ます。YAML 検証を行う場合は PyYAML をインストールしてください。
- process_priority / set_cpu_affinity は権限がない環境や未対応 OS で失敗する可能性がありますが、失敗時は警告を出して処理を継続する設計です。
- logging_setup のログディレクトリ作成に失敗した場合は、ファイル出力が無効になりコンソール（stdout）出力のみになります。
- run_monitoring は監視 DB に常に Settings.sqlite_path を使用します（監視レコードは環境に依存しない設計）。必要に応じて運用ポリシーを調整してください。

今後の予定（例）
----------------
- factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / BrokerClient のインタフェース詳細実装およびテストの充実。
- 単体テストと CI 設定の追加。
- strategy モジュールとの連携サンプル・ドキュメント整備。

Acknowledgements
----------------
- 本 CHANGELOG は現行コードベースの内容より推測して作成しています。実際の設計方針やリリースノートはプロジェクト運用ポリシーに基づいて適宜調整してください。