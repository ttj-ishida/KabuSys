Keep a Changelog — 変更履歴
========================

すべての重要な変更をこのファイルで追跡します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
---------
- 小規模の内部リファクタやログ出力改善など、後続リリースで詳細を追記予定。

0.1.0 - 2026-04-20
-----------------
初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
- 実行／監視エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を分離（data/paper_trading.db をデフォルト）し MockBrokerClient を利用可能。停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、スレッド起動／停止の制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視 DB は環境に関わらず本番 sqlite_path を使用。
- 設定管理
  - config.py: .env 自動読み込み（.env, .env.local、OS 環境変数保護）と Settings クラスを提供。各種環境変数（J-Quants、kabu API、DB パス、監視しきい値など）を安全に取得するヘルパーを実装。PAPER_FILL_MODE 等のバリデーションも実装。
- 設定支援 / 検証 CLI
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。シークレット入力や既存値の再利用、.env ファイル書き込みをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 向けのガードチェックを実装。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）・等金額／スコア重み計算を実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、コストバッファ考慮など実装。
  - portfolio/__init__.py: 上記 API をエクスポート。
- 研究用ファクター計算基盤
  - research/factor_research.py: DuckDB を用いたモメンタム等ファクター計算モジュールを追加（モジュール実装中に一部が含まれる）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数／--db で DB パスを指定可能。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ初期化ユーティリティを追加。コンソール出力は stdout、日次ローテーション（TimedRotatingFileHandler）でログファイル出力（logs/<app_name>.log）をサポート。既存ハンドラの二重登録防止のためクリア処理を行う。LOG_DIR / LOG_LEVEL の環境変数サポート。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定をサポート。権限不足や未対応環境の場合は警告ログを出して安全にスキップ。

Changed
- .env の取り扱いルールを明確化（config.py）
  - 自動ロードの優先順位: OS 環境 > .env.local > .env。OS 環境変数は protected として上書きを防止。
  - .env パーサーで export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応して堅牢化。
- ロギング
  - setup_logging() の既存ハンドラクリアにより、複数回初期化しても二重出力が発生しないように変更。
  - StreamHandler を stdout に向ける設計により、cron 等でのリダイレクト運用を想定。
- 実行／監視プロセスの優先度
  - 起動時に set_process_priority("high") を呼び出すようにして、実行/監視プロセスの優先度を上げる振る舞いを導入。

Fixed
- run_monitoring.py: MONITOR_POLL_INTERVAL の不正な値（0 や負の数、非整数）を検出してデフォルトにフォールバックする処理を追加し、time.sleep に渡す不正値による例外発生を防止。
- logging_setup.py: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソールのみで継続するよう堅牢化。
- process_priority.py: 未対応 OS や権限不足時に例外が上がらず警告でスキップするように修正。

Deprecated
- なし（このバージョンでは非推奨は未導入）

Removed
- なし

Security
- なし（既存のシークレットは .env に記述する前提。config_setup.py で .env の Git コミット禁止を注意書きとして明示）

Notes / 実装上の注意
- 監視（run_monitoring）では monitoring 用 DB の初期化を行うが、実際の SystemMonitor の実装やテーブル定義は別モジュールに依存しているため、環境に応じた DB の準備が必要です。
- Execution 側は paper_trading 環境で paper_fill_mode（PAPER_FILL_MODE）を利用して模擬約定挙動を制御します。有効値の検証が行われます。
- portfolio モジュールは純粋関数群（副作用なし）で設計されており、ユニットテストが容易です。将来的に lot_size を銘柄別に拡張する余地があります（TODO コメントあり）。
- research/factor_research.py は DuckDB 経由のデータ参照を前提とした実装で、prices_daily / raw_financials のスキーマ依存があります。

今後の予定
- SystemMonitor / ExecutionEngine の詳細なユニットテスト追加。
- strategy / execution の統合テスト、モックブローカーの挙動検証ケース追加。
- factor_research の完全実装とデモ用データセット提供。

もし特定の変更点をより詳細に記載してほしい箇所（例: run_execution のリスク設定詳細、position_sizing のスケーリングアルゴリズムの例外ケースなど）があれば教えてください。必要に応じて履歴を追記・分割します。