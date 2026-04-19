CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

Unreleased
----------
- ドキュメント・テスト向けの小さな改善や TODO に関する注記（詳細は各モジュール内コメント参照）。
- research モジュールの一部が未完（calc_momentum の定義途中）で残っています。今後のリリースで完了予定。

0.1.0 - 2026-04-19
-----------------

Added
- 基本アーキテクチャ・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading 時は専用の PAPER_TRADING_SQLITE_PATH を使用）。
  - run_monitoring.py: SystemMonitor をポーリング実行するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）を検出して安全に終了。
- 設定・環境変数管理
  - config.py: .env の自動読み込み（プロジェクトルート検出）と堅牢な .env パーサーを実装。引用符付き値、export 形式、インラインコメントの取り扱い、OS 環境変数保護（override/ protected）に対応。
  - config_setup.py: 対話式ウィザードで .env の作成/更新を支援する CLI を追加。シークレットは表示マスキング、保存時にテンプレートヘッダを付与。
  - validate_config.py: 起動前検証用 CLI を追加。必須環境変数や config/*.yaml の存在・パース（PyYAML がない場合は警告）などをチェック。--strict オプションで警告を失敗として扱う。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: シグナルの候補選定・重み付け（等配分 / スコア加重）。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio.position_sizing: 発注株数計算ロジック（risk_based / equal / score）。単元株（lot_size）丸め、全体キャップ（aggregate cap）に応じたスケーリング・端数処理を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームは警告してフォールバック。
- ユーティリティ
  - utils.logging_setup: stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を組み合わせた統一ログ設定を追加。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils.process_priority: Windows/Linux/Mac の差を吸収したプロセス優先度設定ユーティリティを追加。CPU affinity 設定も提供。権限不足などを安全に無視してログ出力。
- モニタリング・DB
  - monitoring テーブル初期化処理（init_monitoring_db の呼び出しによる冪等なセットアップ）を run_execution/run_monitoring に組み込み。monitoring は環境に関係なく本番 sqlite_path を参照する設計。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。日付フィルタや DB パス指定をサポート。

Changed
- ロギングの出力先と取り扱いを標準化
  - 全ての起動スクリプトが utils.logging_setup.setup_logging を呼び出すことでログの出力形式・ローテーションが統一。
- DB 接続方針
  - 実行系（Execution）は環境が paper_trading の場合に専用の SQLite を使用して本番データと分離。Monitoring は環境に依存せず本番の sqlite_path を使用する旨を明示。

Fixed
- 環境変数関連の堅牢性向上
  - .env のパースで引用符付き値のエスケープ、コメント扱い、export プレフィックスなどに対応。自動ロード時に OS 環境変数を保護するための protected オプションを導入。

Security
- シークレット値の取扱い改善
  - config_setup の対話表示でシークレットはマスクして表示。README 等への誤コミット防止のため .env 生成時に注意書きを追加。

Known issues / TODO
- research.factor_research.calc_momentum がファイル途中で未完の状態（実装継続予定）。
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、前日終値等のフォールバック価格利用が TODO として記載されています。
- position_sizing: 将来的に銘柄毎の lot_size をサポートする設計拡張（TODO コメント）。
- 一部モジュールは外部依存（psutil, duckdb, PyYAML など）へのインストールが前提。依存が無い場合はフォールバックまたは警告で動作継続するが、機能制限が発生します。

開発者向けメモ
- 自動ロードの無効化: テスト等で .env 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベル/ディレクトリの上書き: LOG_LEVEL / LOG_DIR 環境変数で変更可能。
- Kill/Stop フラグおよび PID ファイル: data/stop_requested.flag と data/execution.pid を用いたプロセス制御を採用。

---
この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートとして公開する前に、差分（コミットログ・リリースノート）と照合して確定してください。