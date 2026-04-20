# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog（https://keepachangelog.com/ja/）の形式に準拠しています。

## [0.1.0] - 2026-04-20
初回リリース。自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory によるブローカークライアント生成、スレッドでのセッション実行、停止フラグ（data/stop_requested.flag）検出による安全停止をサポート。
  - ファイル: src/kabusys/run_execution.py

- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB（SQLite）初期化、DuckDB 接続、停止フラグ検出でループ終了。
  - ファイル: src/kabusys/run_monitoring.py

- 設定管理
  - config.py: .env 自動読み込み機能（プロジェクトルート検出）、.env/.env.local の読み込み順序、各種環境変数取得ラッパーを実装。必須変数チェック（_require）や PAPER_FILL_MODE の検証、paper_trading 用 DB パスなどを提供。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加（デフォルト値、シークレットマスク、保存）。
  - validate_config.py: 起動前に .env や config/*.yaml の設定不備を検出する CLI。--strict モードをサポートし、警告を FAIL 扱いにできる。
  - ファイル: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py

- ログ・プロセス管理ユーティリティ
  - logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通関数 setup_logging を追加。ログディレクトリ自動作成と失敗時にファイル出力をスキップするフォールバックを実装。
  - process_priority.py: Windows/Linux/macOS に対応したプロセス優先度設定（psutil 利用）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS に対する警告処理を実装。
  - ファイル: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: 候補選定（スコア降順・タイブレーク）と等金額／スコア重み計算を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: ポジションサイズ計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap（利用可能現金に合わせたスケーリング）と残差処理ロジックを実装。
  - エクスポージャー計算やフォールバック動作（価格欠損時の挙動）についての注釈も含む。
  - ファイル: src/kabusys/portfolio/*.py

- 研究用ファクター計算（下地）
  - research.factor_research: DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 等のファクターを計算するためのモジュール骨組みを追加。モメンタム計算用の定数や設計方針を定義（途中実装あり）。
  - ファイル: src/kabusys/research/factor_research.py

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite(DB) から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値判定（PASS/FAIL）付きでレポートを出力するツールを追加。P95 計算、日付フィルタ、テーブル存在チェックに対応。
  - ファイル: src/kabusys/tools/paper_verification_report.py

- パッケージ化情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に追加。
  - ファイル: src/kabusys/__init__.py

### 変更 (Changed)
- .env 読み込みの堅牢化（config.py）
  - export プレフィックス対応、クォート文字列（シングル/ダブル）およびバックスラッシュエスケープ対応、インラインコメント処理、保護済み OS 環境変数を上書きしないオプションをサポート。
  - 自動ロード順序は OS 環境変数 > .env.local > .env。プロジェクトルートが特定できない場合は自動ロードをスキップ。

- ログ出力の一貫化（logging_setup.py）
  - stdout を StreamHandler に使用（cron 等からのリダイレクト運用を考慮）。
  - ログディレクトリ作成失敗時はファイルハンドラをスキップし、コンソールのみで動作するフォールバックを実装。

- 実行/監視挙動の明文化
  - run_execution/run_monitoring でプロセス優先度を起動直後に high に設定（set_process_priority）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは分離しない方針）。

- RiskManager / ExecutionEngine 周りのデフォルト設定（run_execution.py）
  - RiskConfig のデフォルト値を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 条件, max_drawdown など）。
  - ExecutionEngine の起動前に停止フラグを確認する安全措置を追加。

### 修正 (Fixed)
- .env パーサーの誤解釈回避（config.py）
  - クォートあり/なしでのコメント処理やエスケープ処理の不整合を解消。export KEY=val 形式に対応。

- paper_verification_report の堅牢化
  - テーブルやカラムが存在しない場合でも sqlite3.OperationalError を捕捉してレポート生成を続行するように処理。DB ファイルが存在しない場合の明示的エラーメッセージを追加。

- process_priority / cpu_affinity の例外ハンドリング強化
  - 権限不足や未対応プラットフォームでの例外を捕捉し、警告を出して処理をスキップするように改善。

### ドキュメント・メッセージ (Documentation)
- 各モジュールに日本語の docstring/コメントを充実させ、設計方針・注意点（例えば価格欠損時の影響や Bear レジームでの信号生成方針）を明記。

### 既知の制限 / 注意点 (Known issues / Notes)
- research.factor_research モジュールはモメンタム計算の途中でファイルが切れている（実装継続が必要）。完全な因子計算ロジックは今後追加予定。
- 一部の機能（BrokerClientFactory, ExecutionEngine, SystemMonitor 等）はこの差分で参照はされているが実装ファイルがここに含まれていない可能性がある（別モジュールとして実装される前提）。
- process_priority の一部定数は psutil の OS 固有定数に依存しており、環境に応じたフォールバック動作を行います。権限が不足する場合は設定が反映されないことがあります。

---

今後の予定:
- research モジュールの完成（ファクター算出の最終化、DuckDB クエリ最適化）
- ExecutionEngine 周りの E2E テスト・モック強化
- monitoring の追加メトリクスとアラート通知（LINE 連携など）の拡張

