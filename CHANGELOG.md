CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、リポジトリ内の現在のコード内容から推測して作成した変更履歴です。

Unreleased
----------

- 小さな内部リファクタ（ログメッセージやコメントの改善）
- ドキュメント・CLI ヘルプ文言の微調整

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース: KabuSys 自動売買基盤のコアモジュールを追加。
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV によって paper_trading モードでは MockBrokerClient を使用し、専用の paper_trading DB に記録する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 設定・ユーティリティ
    - config.py: .env 自動読み込み（.env, .env.local）、環境変数取得ヘルパと Settings クラスを提供。PAPER_FILL_MODE 等の検証ロジックを含む。
    - config_setup.py: 対話型ウィザードで .env を初期生成・更新する CLI。
    - validate_config.py: .env と config/*.yaml を起動前に検証する CLI。--strict オプションをサポート。
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティ（stdout と日次ローテートファイル出力）。
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定と等配・スコア配分の重み計算。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウンロジック。
    - portfolio/__init__.py: 上記機能のエクスポート。
  - リサーチ
    - research/factor_research.py: ファクター計算モジュール（モメンタム・ボラティリティ等、DuckDB を用いた計算を想定。実装はファイル内で定義）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、API レイテンシ（P95）などを集約して PASS/FAIL 判定を行う。
  - パッケージ情報
    - __init__.py にバージョン番号 __version__ = "0.1.0" を追加。

Changed
- ログ: setup_logging により stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに統一的に設定。LOG_DIR / LOG_LEVEL の解決順を定義。
- 起動時のプロセス優先度設定: run_execution/run_monitoring の最初で set_process_priority("high") を呼び出すことで、重要プロセスの優先度を高める。
- DB ハンドリング:
  - run_execution は paper_trading 環境のときに settings.paper_sqlite_path を使用して本番 DB と分離。
  - run_monitoring は「監視用途は環境にかかわらず本番 sqlite_path を使用する」という挙動をドキュメント化（監視データは本番 DB に記録）。
- .env 読み込み挙動の改善:
  - .env の行パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行い、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env.local は .env の上書き（override=True）として扱う。
- validate_config CLI:
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）や config/*.yaml の存在・パース確認（PyYAML 未インストール時は警告）を実施。KABUSYS_ENV=live 時の追加警告（LINE 設定や Kill Switch 設定）を実装。

Fixed
- .env パーサにおいてクォートやエスケープの取り扱いを明確にし、コメントの誤扱いを防止。
- ポジションサイズ計算での aggregate cap スケーリング処理を実装。利用可能現金を超える場合にスケールダウンし、残余で lot_size 単位の追加配分を行う（端数処理の再現性を確保）。

Security
- シークレット値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE トークン等）は config_setup の出力でマスク表示（対話中や確認時に **** 表示）。

Documentation
- 各モジュールに日本語ドキュメント文字列を追加。CLI の利用例をヘルプ文字列に明記（例: python -m kabusys.validate_config, python -m kabusys.config_setup, python -m kabusys.tools.paper_verification_report）。

Breaking Changes / Migration Notes
- 監視データの保存先:
  - run_monitoring は監視データに settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します。過去に環境毎に別 DB を使用していた場合は運用ポリシーを確認してください。
- paper_trading 分離:
  - run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用するため、本番 DB と完全に分離されます。既存データ移行が必要な場合は注意してください。
- プロセス優先度設定:
  - set_process_priority は権限が必要な操作（nice 値の低下や Windows の優先度変更）を行うため、権限不足時に警告を出します。CI/コンテナ環境や権限制限のあるホストで起動する際はログの警告を確認してください。
- ログディレクトリ:
  - デフォルトのログ出力先は logs/。ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。運用環境では logs ディレクトリの書き込み権限を確保してください。

Usage Examples
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

Acknowledgements / Notes
- DuckDB と SQLite の両方を使用する設計。duckdb は分析用途、sqlite は監視・取引ログなどの永続記録用を想定。
- 一部モジュール（factor_research 等）は DuckDB のテーブル構造（prices_daily, raw_financials 等）を前提としており、実運用では初期データ投入やスキーマ整備が必要です。

----- 
（この CHANGELOG はコード内容からの推測に基づくもので、実際のコミット履歴とは異なる場合があります。実際の変更履歴はバージョン管理のコミットログを参照してください。）