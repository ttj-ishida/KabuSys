CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して日本語で記載しています。

Unreleased
----------

（特になし）

0.1.0 - 2026-04-19
------------------

初回公開リリース。

Added
-----
- 基本アーキテクチャ・起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は専用の paper DB を使用し MockBrokerClient を利用するよう分離。起動時にプロセス優先度を設定し、別スレッドで engine.run_session を実行、stop フラグ / pid ファイルを扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する設計。
- 設定関連
  - config.py: .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）機能、.env の柔軟なパース（export プレフィックス／クォート／インラインコメント処理）、Settings クラスによる各種設定プロパティを実装（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定など）。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。シークレット項目のマスク表示、デフォルト値や選択肢の提示、保存確認を実装。
  - validate_config.py: 起動前検証 CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）などをチェック。--strict で警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア全0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、レジームに応じた投下資金乗数 (calc_regime_multiplier)。未知レジームはフォールバック処理を備える。
  - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes)。risk_based / equal / score の配分方式、単元株（lot_size）、コストバッファ、aggregate cap（利用可能現金に対するスケーリング）を実装。端数処理やスケールダウン時の再配分ロジックを含む。
  - package エクスポート: kabusys.portfolio から上記関数群を公開。
- 実行時ユーティリティ
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティ。StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/ 日次ローテーション、30日保持）を設定、既存ハンドラをクリアして二重設定を防止。LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで継続する。
  - utils/process_priority.py: Windows / POSIX を抽象化したプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity)。権限不足や未対応プラットフォームに対するフォールバック・警告を実装。
- 分析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、レイテンシ指標（平均・最大・P95）を集計し、閾値（稼働率 99%、成功率 90% など）に基づく PASS/FAIL 判定を出力。P95 計算、日付フィルタ (--from / --to)、DB パスの解決ロジックを提供。
- DB・監視の初期化
  - monitoring_db.init_monitoring_db を使い、監視テーブルが存在することを起動時に保証（冪等）。run_execution では paper_trading 時に paper_sqlite_path を使用して本番 DB と分離。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Deprecated
----------
- （初回リリースのため該当なし）

Removed
-------
- （初回リリースのため該当なし）

Security
--------
- config_setup のウィザードではシークレット値をマスク表示し、.env は絶対に Git にコミットしない旨の注記を出力。
- 環境変数の必須チェック (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) とプレースホルダ検出を行い、未設定・プレースホルダ値の警告/エラーを明示する仕組みを導入。

Notes / 注意事項
----------------
- 実行方法:
  - 監視: python -m kabusys.run_monitoring
  - エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]
- 環境変数の主なもの:
  - KABUSYS_ENV: development | paper_trading | live
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)、SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の fill モード（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（validate_config で警告）
- 既知の制限 / TODO:
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性がある旨を TODO コメントで残している。将来的に前日終値等のフォールバック導入を検討する必要あり。
  - position_sizing の単元株（lot_size）は現在グローバルに固定。将来的に銘柄別 lot_map を導入する余地がある。
  - logging_setup はログディレクトリの作成に失敗した場合ファイル出力をスキップするが、ある環境では出力先の権限/パスの事前確認が必要。
  - process_priority / cpu_affinity は権限やプラットフォーム差分で動作しない場合がある。実行環境での権限設定を確認してください。

もしこの CHANGELOG に追加したい差分（実際の変更履歴やリリース日付の調整、貢献者の明記等）があれば教えてください。コードベースから推測できた範囲で記載しています。