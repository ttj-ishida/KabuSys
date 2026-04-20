Keep a Changelog に準拠した CHANGELOG.md（日本語）
=======================================

フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-20
--------------------

Added
- 実行エンジン: ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の SQLite（既定: data/paper_trading.db）に記録することで本番 DB と完全に分離。
  - 起動時にプロセス優先度を "high" に設定する処理を導入。
  - 実行中の停止を data/stop_requested.flag で検出し、PID ファイル管理と安全な停止処理を実装。
  - RiskManager / Reconciler / OrderManager / OrderRepository などの組み立てロジックと既定のリスク設定値（最大保有比率・利用率・サーキットブレーカー等）を追加。

- 監視サービス: SystemMonitor のポーリング起動スクリプトを追加（src/kabusys/run_monitoring.py）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
  - 監視は環境設定にかかわらず本番 sqlite_path を参照（監視データは production 用監視 DB に保存）。
  - 停止フラグ検出および例外ハンドリングを実装。

- 設定管理: 環境変数/.env の自動ロードと Settings クラスを実装（src/kabusys/config.py）。
  - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local の順、OS 環境変数は保護）。
  - export 形式、クォート（シングル/ダブル）やバックスラッシュエスケープ、行内コメントの取り扱いに対応するパーサ実装。
  - 各種設定プロパティ（J-Quants / kabuAPI / DB パス / Paper Trading オプション / 監視スレッショルド等）を提供。
  - PAPER_FILL_MODE の値検証、KABUSYS_ENV / LOG_LEVEL の検証とヘルパープロパティ（is_live / is_paper / is_dev）。

- 設定ウィザード: .env を対話式に生成/更新する CLI を追加（src/kabusys/config_setup.py）。
  - 一覧表示、既存値の再利用、シークレットのマスク表示、保存前確認などのインタラクティブ操作を提供。

- 設定検証 CLI: 起動前に .env と config/*.yaml を検証するツールを追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML 未インストール時はスキップ）を実装。
  - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - 候補選定: スコア降順かつ signal_rank によるタイブレークで上位 N 件を選択する select_candidates を実装。
  - 重み計算: 等分配 calc_equal_weights、スコア正規化 calc_score_weights（全スコア 0 の場合は等分配へフォールバック）を実装。
  - ポジションサイズ計算: calc_position_sizes を実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）。
  - リスク調整: セクター上限 apply_sector_cap、レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）を実装。

- ロギングユーティリティ: 統一的なログ設定関数を追加（src/kabusys/utils/logging_setup.py）。
  - stdout への StreamHandler（stdout 使用）と日次ローテーションされるファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
  - LOG_DIR 作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - ログレベル解決（引数 > 環境変数 > デフォルト）をサポート。

- プロセス優先度/CPU 固定ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX（Linux/Mac/FreeBSD）対応でプロセス優先度を設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。権限不足や未対応プラットフォームは警告でスキップ。

- Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
  - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシを計算してレポート出力。
  - P95 計算や日付フィルタ（--from / --to）対応、DB パスの解決ロジック（引数 > 環境変数 > デフォルト）を実装。
  - 基準値（稼働率 >=99%、注文成功率 >=90% など）に基づく PASS/FAIL 判定を出力。

- 研究用ファクタ計算モジュール骨組み（src/kabusys/research/factor_research.py）
  - Momentum/Value/Volatility/Liquidity 等の計算方針を実装するための関数スケルトンを追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。

Changed
- データベースの取り扱い:
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計に明示化。
  - ExecutionEngine は paper_trading モード時に専用の paper_sqlite_path を使用することで本番 DB と分離。

- .env 自動ロードの優先度:
  - OS 環境変数を保護しつつ .env / .env.local を自動で読み込む挙動を採用（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメントの扱いを改善。
  - 無効行や空行、コメント行を正しく無視するように修正。

- ログ出力の堅牢化:
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合、安全にコンソールのみで動作を継続するフォールバックを追加。
  - stdout を用いることでスケジューラからのリダイレクト運用を考慮。

Notes
- コマンド例:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

今後の予定（想定）
- research/factor_research の全指標実装と単体テスト追加
- ExecutionEngine / SystemMonitor の統合テスト強化
- 銘柄毎の単元株情報を取り扱うための拡張（lot_size をマスタ化）
- エラーメトリクスやアラートの強化（LINE 通知活用の拡充）

---------------------------------------
（注）上記は提供されたコードベースの内容から推測して作成した変更履歴です。実際のリリースノートやバージョン履歴に合わせて適宜調整してください。