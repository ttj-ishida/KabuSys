CHANGELOG
=========

すべての重要な変更はこのファイルに記録します（Keep a Changelog 準拠）。
訳注: 以下の履歴は与えられたコードベースの内容から推測して作成しています。

[Unreleased]
-------------

- ドキュメント・軽微な整備やリファクタの予定（特記事項なし）。

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリース。以下の主要コンポーネントを追加。
  - 実行/監視用エントリポイント
    - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB (data/paper_trading.db) と完全分離して動作する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。
  - 設定管理
    - config.py: Settings クラスを導入。環境変数・.env ファイルの自動ロード（優先順位: OS 環境変数 > .env.local > .env）と各種プロパティ（DB パス、KABUSYS_ENV、ログレベル、paper_trading 関連設定など）を提供。PAPER_FILL_MODE 等の入力検証あり。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - config_setup.py: 対話式 .env 作成ウィザード（秘密値のマスク表示や既存値の再利用対応）。
    - validate_config.py: 起動前検証 CLI。必須環境変数、KABUSYS_ENV 値、パスの存在、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）などをチェック。--strict オプションで警告を FAIL 扱いにできる。
    - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理ルール等を実装。
  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py: 標準化されたログ設定ユーティリティ。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。CPU affinity を設定する set_cpu_affinity も提供。権限不足や未対応環境では安全にフォールバックして警告出力。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py: シグナルのソート・候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金倍率 calc_regime_multiplier を実装（unknown レジームはフォールバック扱い）。
    - portfolio/position_sizing.py: allocation_method に基づく株数算出ロジック（risk_based / equal / score）、単元株丸め、per-position 上限・aggregate cap（available_cash に合わせたスケーリング）、cost_buffer による保守的見積り、残余配分ロジック等を実装。lot_size といった将来的拡張ポイントに注記あり。
    - portfolio/__init__.py: 上記 API を外部公開。
  - Execution 系コンポーネントの組立（スクリプトから使用）
    - run_execution で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててエンジンを実行。停止フラグによる安全停止処理を実装。
  - 監視系
    - run_monitoring が monitoring DB の初期化（init_monitoring_db）を行い、SystemMonitor.check_once() を定期実行。
    - 停止フラグファイル（data/stop_requested.flag）検知によるループ終了対応。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する閾値（稼働率 99%、成功率 90% 等）を定義。P95 計算、日付フィルタ指定、DB パス解決ロジック等を実装。
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（Momentum、Value、Volatility、Liquidity 計算方針とスキャン範囲等を定義）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照する設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数ファイル (.env) 生成時に秘密値をマスク表示するなど、秘密情報の扱いに配慮した UI を提供。

Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で終了している箇所（未完）あり。ファクター計算の完全実装は今後の作業が必要。
- 一部の TODO（例: position_sizing の銘柄別 lot_size マスタ対応、price 欠損時のフォールバック価格使用など）が残っている。
- run_execution 側で PID ファイルや ExecutionEngine の内部実装に依存する箇所があるため、実運用前に Engine/ Broker の実装と統合テストが推奨される。
- ログディレクトリ作成やプロセス優先度設定は環境や権限に依存するため、失敗時は警告してフォールバックする設計。CI やコンテナ環境での挙動確認を推奨。

Package
- __version__ = "0.1.0"

（以上）