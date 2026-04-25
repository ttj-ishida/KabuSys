CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このファイルは "Keep a Changelog" に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現時点の開発中の変更はここに記載してください）

[0.1.0] - 2026-04-25
-------------------

Added
- 初回リリース。パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として追加。
- 起動スクリプト:
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag により行う。
  - run_execution.py を追加。ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用に分離された SQLite（デフォルト: data/paper_trading.db）を利用する。起動時にプロセス優先度を "high" に設定し、PID ファイルを出力する。
- 設定管理:
  - src/kabusys/config.py を追加。.env/.env.local 自動読み込み（プロジェクトルート検出）、堅牢な .env パーサ実装（クォート、エスケープ、export プレフィックス、インラインコメント等に対応）。Settings クラスを提供し各種環境変数をプロパティ経由で取得・検証（J-Quants / kabu API / DB パス / PAPER_FILL_MODE 等）。
  - config_setup.py を追加。.env の対話式ウィザード（初期作成・更新）を実装。複数の設定項目を扱い、シークレットはマスクして表示・保存する。
  - validate_config.py を追加。起動前の設定検証用 CLI。必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML によるパース検証、KABUSYS_ENV=live 時の追加ガード等を実装。--strict フラグで警告を FAIL 扱いにできる。
- ロギングとプロセス管理ユーティリティ:
  - utils/logging_setup.py を追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート・30 日保持）を設定。ログレベル / ログディレクトリの解決優先順を実装。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py を追加。psutil を用いたクロスプラットフォームのプロセス優先度設定（high/normal/low）と CPU affinity 固定機能。アクセス権限不足などの場合は安全にフォールバックして警告を出力。
- ポートフォリオ構築ライブラリ（純粋関数群）:
  - portfolio/portfolio_builder.py: シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア合計がゼロの場合のフォールバック処理を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた資金乗数を返す calc_regime_multiplier を追加。未知レジーム時のフォールバックとログ出力を実装。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数計算 calc_position_sizes を追加。単元株切り捨て、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、残差配分ロジックを実装。
  - portfolio/__init__.py で上記関数群を公開。
- 分析・検証ツール:
  - tools/paper_verification_report.py を追加。Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）を参照して稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、PASS/FAIL 判定を行う CLI レポートを実装。期間指定の --from / --to、DB パス上書きオプションを提供。P95 の計算ロジックと、DB が存在しない場合の親切なエラーメッセージを備える。
- 研究用モジュール（骨格）:
  - research/factor_research.py を追加。DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）を想定した設計と一部実装（モメンタム計算の仕様記述を含む）。DuckDB 接続を受け取り SQL+Python で計算する方針。

Changed
- ログ出力先の StreamHandler を stderr ではなく stdout に明示（logging_setup.py）。cron/Task Scheduler 等での stdout/stderr 統合を想定。

Fixed
- （このバージョンでは既知のバグ修正はなし。リリース前の安定化は今後のバージョンで行う予定）

Deprecated
- なし

Removed
- なし

Security
- .env ファイルは絶対にリポジトリにコミットしない旨を config_setup の生成ヘッダに明記（config_setup.py、.env 書き込みテンプレート）。

Notes / 備考
- run_monitoring/run_execution は外部依存（duckdb, psutil, sqlite3, logging 等）を用いるため、実行環境にこれらをインストールしておく必要があります。
- Settings クラスは環境変数の検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を行うため、不正な値は ValueError を発生させます。デプロイ前に validate_config を実行して設定を確認してください。
- position_sizing や risk_adjustment は純粋関数として DB 参照を行わない設計のため、ユニットテストの作成・実行が容易です。

今後の予定（例）
- factor_research の完全実装（各ファクターの SQL 実装、Zスコア正規化との統合）
- ExecutionEngine の詳細な統合テスト、BrokerClient のモック改善
- モニタリング・アラートの LINE 通知実装（環境変数 LINE_* を利用）
- ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）の追加・整備

--- End of CHANGELOG ---