Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

フォーマットのルール:
- 変更は "Added", "Changed", "Fixed", "Deprecated", "Removed", "Security" のカテゴリに分類します。
- バージョンごとに日付を付けます。

Unreleased
---------

- （今後の変更点のためのプレースホルダ）

0.1.0 - 2026-04-20
-----------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの主要コンポーネントを追加。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使用する（分離されたペーパートレードDB: data/paper_trading.db をデフォルト）。停止フラグ / PID 管理、スレッドでのエンジン実行と安全な停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出で安全にループ終了。
- 設定関連:
  - config.py: 環境変数読み込み・管理クラス Settings を追加。自動 .env ロード（プロジェクトルート検出）、必須変数チェックヘルパ、paper_trading 用設定、閾値等のプロパティを提供。
  - config_setup.py: .env の対話式ウィザードを追加（生成・更新・ファイル書き込みをサポート）。機密値はマスク表示。保存前の確認を実装。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在（および PyYAML があればパース検査）等をチェック。--strict オプションで警告も失敗扱いに可能。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全0時のフォールバック警告あり。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームのフォールバック動作を明示。
  - portfolio/position_sizing.py: 株数決定ロジック calc_position_sizes を追加。allocation_method に "risk_based", "equal", "score" をサポート。単元株丸め、1銘柄上限、aggregate cap（利用可能現金）によるスケーリング、cost_buffer による保守的見積り、残差処理による追加配分処理を実装。
- 研究用モジュール（部分実装）:
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子（モメンタム、MA200乖離、ATR 等の定義と設計方針）。（実装の継続を予定）
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ (avg / max / P95) の集計と Pass/Fail 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を備える。
- ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテーション（TimedRotatingFileHandler）でログを logs/<app_name>.log に出力。ログディレクトリ作成失敗時はファイル出力をスキップして継続する安全な実装。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。Windows/Linux(macOS/FreeBSD) に対応し、権限不足等で設定できない場合は警告ログでフォールバック。

Changed
- ログ管理方針: 全スクリプトは setup_logging を呼び出すことで統一的なログ出力を行うよう設計。
- 環境読み込み優先順位: OS 環境 > .env.local > .env の順で読み込む実装。既存 OS 環境キーは保護（上書き防止）。

Fixed
- 環境変数パースの堅牢化（config._parse_env_line）:
  - export KEY=val 形式をサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善。
  - クォートなし値のコメント検出ルールを明確化。
- MONITOR_POLL_INTERVAL の不正値対策:
  - run_monitoring のポーリング間隔取得で 0 以下や非整数を警告してデフォルトにフォールバックする実装を追加。
- PAPER_FILL_MODE のバリデーション:
  - 許容値を列挙して不正な値は ValueError を発生させるようにし、不正設定の早期検出を可能に。
- run_execution:
  - 起動時に停止フラグが既に立っている場合はエンジンを起動せず終了する安全処理を追加。
  - スレッド終了待機とタイムアウト（30 秒）を実装してシャットダウンを安定化。

Security
- .env の扱いに関する注意書きを config_setup に明記（.env を絶対に Git にコミットしないよう指示）。
- 対話ウィザードは機密値を画面表示時にマスク。

Notes / Upgrade
- 初回セットアップ:
  - .env を作成していない場合は python -m kabusys.config_setup を実行してウィザードで生成してください。
  - 設定検証は python -m kabusys.validate_config で実行できます。
- 実行:
  - 監視ループ: python -m kabusys.run_monitoring
  - エンジン:    python -m kabusys.run_execution
  - Paper 検証:  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- ログ:
  - デフォルトのログディレクトリは logs/。環境変数 LOG_DIR で変更可能。ファイル出力ができない場合はコンソールのみで継続します。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用の SQLite (PAPER_TRADING_SQLITE_PATH) に記録され、本番 DB と分離されます。

Acknowledgements
- この CHANGELOG はソースコードの実装内容から推測して作成しています。実際の変更履歴（コミットログ等）とは差異がある場合があります。