CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（未リリースの変更はここに記載します）

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリースを追加。
- 実行用・運用用の起動スクリプトを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 経由で発注をシミュレーション。エンジンはスレッドで実行され、 data/stop_requested.flag による外部停止、pid ファイルの管理をサポート。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。monitoring は環境に依存せず本番用 sqlite_path を使用して監視データを保存。
- 設定管理まわり:
  - config.py: .env 自動ロード機能（.env / .env.local）、OS 環境変数保護（上書き禁止）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を提供する Settings クラスを追加。
  - config_setup.py: 対話式の .env ウィザード（.env の初期作成/更新）を提供。秘密値マスク表示、既存値の再利用、選択肢サポートなど。
  - validate_config.py: 起動前に .env と config/*.yaml の検証を行う CLI。--strict オプションで警告をエラーとして扱える。PyYAML 未インストール時の挙動や本番環境向けのガードチェックを実装。
- ロギング／プロセス管理ユーティリティ:
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティ。ログレベル/ログディレクトリの解決順を実装し、ファイル出力作成に失敗してもコンソールログで継続する保守性を確保。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築関連（純関数群、DB 非依存）:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア重み (calc_score_weights) を実装。スコア全てが 0 の場合は等分配へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバック挙動を定義。
  - portfolio/position_sizing.py: allocation_method (= "risk_based" / "equal" / "score") に対応した株数決定ロジックを実装。単元株（lot_size）、損切り率・リスク許容率、新規投下上限（max_position_pct）、aggregate cap によるスケールダウン、手数料・スリッページ考慮（cost_buffer）と残差処理アルゴリズムを提供。
- 解析・検証ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト。稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/p95）などを集計し、閾値（デフォルト: 稼働率 99%、fill 90%、send 95%、P95 200ms）で PASS/FAIL を判定。日付フィルタ（--from/--to）と DB パスの指定をサポート。
- research/factor_research.py: DuckDB 接続を受け、prices_daily / raw_financials を用いてモメンタム等のファクター計算を行うための雛形関数を追加（関数群の一部は設計に沿って実装中）。

Changed
- なし（初版のため変更履歴なし）。

Fixed
- なし（初版のため修正履歴なし）。

Notes / 備考
- 環境分離:
  - paper_trading モードでは発注履歴等を本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。これにより開発・検証時に本番データを汚染しない。
  - ただし monitoring（run_monitoring）は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用する実装になっているため、環境の運用ポリシーに応じて挙動に注意が必要。
- ロギング:
  - ログ出力先ディレクトリ作成に失敗した場合は自動的にファイル出力を無効化してコンソール表示のみで継続するため、権限/ディスク問題があってもプロセスは停止しない設計。
- .env パーサ:
  - シングル/ダブルクォート内のエスケープやインラインコメント処理を考慮した .env ファイルの堅牢な読み込みロジックを実装。既存 OS 環境変数を保護するための protected 上書き禁止機能あり。
- 安全ガード:
  - validate_config の本番向けガードや config.Setup の KILL_FLAG_CLEAR_ON_START など、本番での誤設定を検出・警告するチェックを実装。

今後の予定（提案）
- research/factor_research の完全実装（ファクター計算ロジックの SQL/最適化）。
- 発注ロジック・ブローカークライアントの詳細なモック実装と、execution/ の統合テスト追加。
- 単体テスト・CI の追加と、config/*.yaml のスキーマ検証強化。
- ドキュメント改善：PortfolioConstruction.md / StrategyModel.md などの参照セクションを README にまとめる。

--- 

（注）本 CHANGELOG は提示されたコードベースの実装内容から推測して作成しています。実際の履歴・リリース日・詳細はプロジェクトの正式なリリースノートに合わせて調整してください。