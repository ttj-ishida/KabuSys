CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（次回リリースに向けた未公開の変更点をここに記載します）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys のコアユーティリティ・CLI・モジュール群を追加。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient（分離された SQLite DB）を使用する挙動をサポート。
      - 起動前にプロセス優先度を "high" に設定。
      - 停止フラグ (data/stop_requested.flag) を監視して安全にシャットダウン。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記。
  - 設定管理
    - config.py: 環境変数・設定管理モジュールを追加。
      - .env 自動ロード（.env.local → .env）機能（プロジェクトルートを自動検出）。
      - 複数のプロパティ（DB パス、ログ設定、Paper Trading の挙動等）を提供。
      - PAPER_FILL_MODE の検証（有効値チェック）等の堅牢なバリデーションを実装。
    - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
      - J-Quants / kabu API 等の必須項目、デフォルト値、シークレット入力に対応。
  - 設定検証ツール
    - validate_config.py: 起動前検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、config/*.yaml の存在/パース（PyYAML があればパース検証）等を実行。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等ウェイト/スコア加重の重み計算を実装。
    - portfolio.risk_adjustment: セクター上限の適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。
    - portfolio.position_sizing: 発注株数計算ロジック（risk_based / equal / score）を実装。lot_size、コストバッファ、aggregate cap のスケーリングロジック等を含む。
    - portfolio パッケージでまとめてエクスポート。
  - 研究用モジュール
    - research.factor_research: DuckDB を用いたファクター計算の骨組み（モメンタム / MA / ATR / 流動性等）を追加（設計方針・定数を含む）。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、レイテンシ（平均/MAX/P95）、リスク却下数等を集計して PASS/FAIL 判定を出力。
      - --from / --to / --db オプションで期間・DB を指定可能。
  - ユーティリティ
    - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
      - stdout（StreamHandler）へ出力、日次ローテーションの TimedRotatingFileHandler（既定 logs/、30日保持）を設定。
      - ログディレクトリ作成失敗時はファイルハンドラをスキップして安全に動作。
      - stdout を使用することでスケジューラからのリダイレクト運用を想定。
    - utils.process_priority: クロスプラットフォームのプロセス優先度 / CPU affinity 設定ユーティリティを追加。
      - Windows / POSIX の差分を吸収し、psutil エラー時は警告を出してスキップ。
  - DB 周り
    - DuckDB と SQLite の両方を利用する設計を導入（duckdb_path, sqlite_path）。
    - monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを起動時に行い、冪等的にテーブル存在を保証。

Changed
- 設計/動作上の決定を明確化。
  - run_monitoring は環境に関係なく「production（本番）用の sqlite_path」を使用する仕様として明示（監視は常に本番データを見るため）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して、本番 DB と完全分離する挙動を実装。
- .env の自動ロード順序を明確化（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- logging_setup のデフォルト挙動を明確化（ログレベル解決順、ログディレクトリ解決順）。

Fixed
- 環境変数パーサーの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などに対応。
- 起動スクリプトの安全性向上
  - 停止フラグ（data/stop_requested.flag）検知による安全停止ループを実装。
  - MONITOR_POLL_INTERVAL の不正値（負数・非整数）を検出してデフォルトにフォールバックし、警告を出力するようにした。
- ログ設定でディレクトリ作成失敗時にファイル出力を無効化してもプロセスが継続するようにした（運用環境での堅牢性向上）。
- process_priority にて未対応 OS の場合に警告を出してスキップする安全措置を追加。
- validate_config: PyYAML が無い場合は YAML 検証をスキップして警告を出すようにして依存性に柔軟性を持たせた。

Security
- config_setup にヘッダコメントを追加し、.env を絶対に Git にコミットしない旨を明示。
- Settings._require によって必須環境変数が未設定の場合は起動前に明確に例外を投げるようにし、誤設定による不要な実行を防止。

Notes
- research.factor_research モジュールは設計と定数まで含まれており、実装の続きを想定（prices_daily / raw_financials を使用する設計）。
- 一部モジュール（ExecutionEngine 本体、BrokerFactory、OrderManager 等）は参照され利用される前提で組み立てられているが、本 CHANGELOG はリポジトリ内に存在するコードから推測した機能と変更を記述しています。

参考
- 本ファイルは Keep a Changelog のスタイルに従っています（https://keepachangelog.com/）。