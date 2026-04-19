CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に従います。
リリースの安定化・追跡のため、主な追加機能・修正点を日本語でまとめています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、ExecutionEngine の起動・停止監視（stop flag / PID ファイル対応）を実装。
  - run_monitoring.py: SystemMonitor 起動スクリプトを追加。ポーリングループ、MONITOR_POLL_INTERVAL 環境変数による間隔上書き、停止フラグ検査、監視 DB 初期化を実装。
  - 停止制御ファイル: data/stop_requested.flag と実行用 PID ファイルを用いた安全停止フローを搭載。
- 環境設定関連 CLI
  - config_setup.py: 対話式 .env ウィザードを追加。.env の読み込み・更新・テンプレート出力機能（機密項目のマスク表示、デフォルト・選択肢対応）。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加（必須環境変数チェック、パス存在チェック、YAML パース検証、live 環境向けガード等、--strict オプションあり）。
- 設定管理
  - config.py: 環境変数自動ロード（プロジェクトルート判定: .git または pyproject.toml 基準）、.env/.env.local の読み込みルール（OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）、各種設定値（DB パス、ログレベル、paper_trading 用 DB、監視閾値 等）を提供する Settings クラスを追加。入力検証（列挙値チェックや必須値チェック）を実装。
  - .env パースの強化: export プレフィックス、引用符付き値（エスケープ処理含む）、インラインコメントルールに対応。
- Paper Trading 分離
  - run_execution の起動時、KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離して動作可能に。
  - Broker の Mock 実装（ファクトリ経由想定）を想定した設計。
- 監視・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値比較で PASS/FAIL 判定を行う。P95 計算、日付フィルタ、DB パス指定オプションをサポート。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア順ソート）、等金額・スコア加重の重み計算（スコア全体が 0 の場合は等分へフォールバック）。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め（lot_size）、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）や cost_buffer による保守的見積り、端数配分アルゴリズムを実装。
  - portfolio/risk_adjustment.py: セクター上限適用（既存保有のセクター比率に基づく候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジーム時のフォールバックとログ警告あり。
  - portfolio/__init__.py: 上記関数群をパッケージ公開。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテート、既定 logs/、30日保持）をルートロガーに設定する。既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック対応、環境変数 LOG_LEVEL / LOG_DIR を優先する解決ロジックを実装。
  - utils/process_priority.py: psutil を利用したプロセス優先度設定（Windows の priority class / POSIX の nice）、および CPU affinity 固定機能を追加。プラットフォーム差分吸収、権限不足や未対応環境での安全フォールバックを実装。
- research/factor_research.py（骨格）
  - DuckDB を利用したファクター計算モジュールの骨格を追加。モメンタム、MA200 乖離、ATR、流動性等の計算方針を定義。calc_momentum の実装開始（ファイル末尾で未完の部分あり）。
- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- その他
  - DuckDB / sqlite3 を併用する設計（分析用は DuckDB、監視/取引ログは SQLite）。
  - 各モジュールで詳細なログメッセージとエラーハンドリングを整備。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Notes / 注意点
- .env ファイルには機密情報（API トークン等）を含むため、必ず .gitignore 等でバージョン管理対象外としてください（config_setup の出力ヘッダにも注意喚起あり）。
- run_monitoring は常に本番用 sqlite_path を使用する設計になっているため、paper_trading 環境でも監視 DB は本番パスを参照する点に注意してください（設計上の意図として明記）。
- process_priority / cpu_affinity の設定は権限に依存するため、実行環境での権限不足時は警告ログを出して操作をスキップします。
- research/factor_research.py の一部は未完（calc_momentum の続き）ため、実運用前に完成・テストが必要です。

--- 

今後の予定（例）
- ファクター計算モジュールの完成とユニットテスト追加
- ExecutionEngine / SystemMonitor のエンドツーエンドテスト、及び Broker の Mock 実装強化
- 設定検証の拡張（config YAML のスキーマバリデーション等）
- ドキュメント（運用手順、デプロイ手順、監視・障害対応）の整備

関連ファイル
- 主要エントリ: run_execution.py, run_monitoring.py, config_setup.py, validate_config.py, tools/paper_verification_report.py
- ライブラリ: portfolio/*, utils/*, research/*

（以上）