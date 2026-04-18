CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョンはパッケージの __version__ = "0.1.0" に合わせています。

Unreleased
----------

（現在なし）

[0.1.0]
------
リリース: 初回リリース

Added
- kabuys 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を想定して本番 DB と完全に分離する。
    - プロセス優先度を "high" に設定してから起動する。
    - 停止制御: data/stop_requested.flag の存在を検出すると安全に停止する。execution.pid を PID ファイルとして利用。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててバックグラウンドスレッドで実行する。

- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する挙動（監視データは本番 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了する。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（protected keys）に対応。
    - .env のパース機能を独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントのルールをサポート）。
    - Settings クラスを提供し、環境変数に対するリッチなプロパティ（パス解決、型変換、バリデーション、env 判定ヘルパ等）を実装。
    - paper_trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）をサポート。

- 設定ユーティリティ CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - シークレット入力の扱い、選択肢・デフォルト値の提示、既存 .env の取り込み、書き込みテンプレートを提供。
    - .env の保存をユーザー確認の上で実行。

  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計してレポート出力。
    - 指標に対する PASS/FAIL 判定基準を定義（稼働率 >= 99%、成立率 >= 90% など）。
    - --from / --to / --db オプションで期間・DB を指定可能。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアがすべて 0 の場合は等金額にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（当日売却予定銘柄の除外や "unknown" セクターの扱いを定義）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score の両方式）を実装。
    - 単元株（lot_size）丸め、per-position と aggregate のキャップ適用、available_cash に基づくスケールダウン、cost_buffer（手数料・スリッページ）考慮など多くの実運用上の制約を含む設計。

  - portfolio/__init__.py で上記機能をエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを提供。
    - コンソール出力は stdout、ファイル出力は日別ローテーション（TimedRotatingFileHandler）で 30 日保持。
    - LOG_DIR 指定またはデフォルト logs/ を使用。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py
    - psutil を用いてプロセス優先度設定と CPU affinity 設定を抽象化（Windows / POSIX の差分を吸収）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足等の失敗時は警告を出して安全にスキップ。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB 接続を使ったファクター計算の枠組み（モメンタム、MA200乖離、ATR、出来高等）を用意。モジュールは設計ドキュメント（StrategyModel.md / PortfolioConstruction.md）に基づいている。コードは途中まで実装済み（以降の実装は継続想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / その他
- .env 自動ロードはデフォルトで有効。ただしテストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できる。
- run_monitoring と run_execution は共に起動前にプロセス優先度を "high" にしようとする（権限やプラットフォームにより失敗する可能性があるが、欠落時は警告でスキップ）。
- ログ設定は起動スクリプトから必ず setup_logging(app_name=...) を呼ぶ想定。ログファイルの作成に失敗してもコンソール出力は行われるように設計。
- 設定検証（validate_config）は PyYAML の有無に応じて YAML 検証をスキップ可能。YAML パース時の例外はエラー扱いとして報告する。

今後の改善案（予定）
- research/factor_research の完全実装（ファクター計算関数群の完成）。
- ポートフォリオ構築における銘柄個別 lot_size 対応（stocks マスタの導入）。
- 価格欠損時のフォールバック価格使用（前日終値等）によるエクスポージャー計算の堅牢化。
- より詳細な単体テストとドキュメント（API 使用例・設計ドキュメントのリンク）を追加。

--- 

（この CHANGELOG は与えられたコードベースから推定して作成しています。実際のコミット履歴や追加のファイルが存在する場合は適宜補完してください。）