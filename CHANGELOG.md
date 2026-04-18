Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました（日本語）。リポジトリの現状コードから推測して記載しています。

お使いのリポジトリのバージョンは src/kabusys/__init__.py の __version__ に基づき 0.1.0 としています。日付は本日（2026-04-18）をリリース日として記載しています。必要に応じて日付や項目を調整してください。

----------------------------------------------------------------------
CHANGELOG.md
----------------------------------------------------------------------

Keep a Changelog
=================
すべての重要な変更をここに記録します。  
フォーマットは https://keepachangelog.com/ja-1.0.0/ に準拠します。

ルール: セマンティックバージョニングを使用します。

Unreleased
----------
（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------
Added
- 初期リリース: KabuSys v0.1.0 を追加。
- コア設定管理:
  - Settings クラスを実装。環境変数経由の設定取得を提供（J-Quants / kabuステーション / DB パス / ログ設定など）。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml ベース）。`.env` と `.env.local` の読み込みルールを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env 行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント扱いの細かい扱い）。
  - 各種プロパティで入力値の検証を実施（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
- 設定ユーティリティ・CLI:
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
  - validate_config: .env と config/*.yaml の事前検証を行う CLI を追加。--strict オプションで警告を FAIL 扱いにする機能を提供。
- 実行スクリプト:
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を利用（本番 DB と分離）。BrokerClientFactory により実ブローカー／モックを切り替え。停止フラグ、PID ファイル、デーモンスレッドでの実行制御をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
- 監視/DB 初期化:
  - init_monitoring_db を呼び出して監視テーブルの存在を保証する仕組みを実装（冪等）。
  - duckdb 接続サポートを追加（分析用 DB）。
- ロギングとプロセス制御ユーティリティ:
  - logging_setup: ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時は安全にフォールバックして標準出力のみ動作する。
  - process_priority: psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）と set_cpu_affinity を追加。アクセス権限エラー時は警告を出してスキップする堅牢な実装。
- ポートフォリオ構築モジュール:
  - portfolio_builder: select_candidates（スコア降順で候補選定）、calc_equal_weights、calc_score_weights（スコア和が 0 の場合は等金額にフォールバック）を実装。
  - risk_adjustment: apply_sector_cap（セクター集中制限の適用／除外、"unknown" セクターの扱い）、calc_regime_multiplier（market regime に基づく資金乗数と既定のマッピング）を実装。
  - position_sizing: calc_position_sizes（risk_based / equal / score 各方式をサポート、単元株（lot_size）丸め、1 銘柄上限・集合上限のスケールダウン、cost_buffer に基づく保守的見積り等）を実装。
- ペーパートレード検証ツール:
  - tools/paper_verification_report: Paper Trading DB（デフォルト data/paper_trading.db）に対する検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL を判定する。しきい値はソース内で定義（稼働率 99%、成立率 90% など）。
- 研究用ファクター計算（初期実装）:
  - research/factor_research: モメンタム／移動平均／ATR などの計算に着手。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを返す設計（calc_momentum 関数等、実装開始）。
- パッケージ情報:
  - パッケージ初期化に __version__ = "0.1.0" を設定。主要サブパッケージの __all__ を定義。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- （初期リリースのため修正履歴はなし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes
- run_monitoring と run_execution は stop flag（data/stop_requested.flag）や PID ファイルを用いた外部制御を想定しています。デプロイ時は該当ディレクトリのパーミッションや運用フローを確認してください。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後やパッケージ化された環境での挙動に注意）。
- process_priority / cpu_affinity の設定は権限によって失敗する場合があります（ログに警告を出してスキップする設計）。
- research/factor_research の一部は実装が途中（ファイル末尾が切れている）と思われます。実際のファクター計算を利用する際は未実装箇所の確認とテストを行ってください。

----------------------------------------------------------------------
（この CHANGELOG はコードの内容から推測して自動生成しました。必要に応じて内容の修正・補完をお願いします。）