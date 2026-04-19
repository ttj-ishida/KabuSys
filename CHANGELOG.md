CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 初回リリース
-------------------

Added
- コア機能・モジュールを追加
  - kabusys パッケージの初回実装。
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全に分離する設計。
    - 停止制御は data/stop_requested.flag と data/execution.pid を使用。
    - プロセス優先度を起動時に "high" に設定。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ (data/stop_requested.flag) の検知でループを終了。
    - プロセス優先度を "high" に設定して起動。

- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - J-Quants / kabuステーション / DB パス / LINE 等の主要設定を対話的に設定可能。シークレット項目はマスク表示。
    - .env 書き出しテンプレートを同梱（.env を絶対にコミットしない旨の注記あり）。

  - validate_config.py
    - .env および config/*.yaml の起動前チェック CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML 未インストール時は警告）などを行う。
    - --strict オプションで警告も失敗扱いにできる。

- 環境読み込み・設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づいて .env/.env.local を自動読み込み（OS 環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env 行パース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いの細かい仕様）。
    - Settings クラスを導入し、アプリ全体で利用する設定プロパティ群を提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境フラグ等）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）と paper_sqlite_path の分離。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（logs/<app_name>.log、日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。
    - ログレベル / ログディレクトリの解決順序（引数 > 環境変数 > デフォルト）に対応。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count: int|None) を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全0時は等配分へフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を実装する apply_sector_cap。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 で警告フォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮。
    - スケーリング時の端数処理（lot_size 単位で残差に基づく追加配分）を実装。

- 解析・リサーチ
  - research/factor_research.py（骨格実装）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム・ボラティリティ等のファクター計算を行う設計（モジュール化、定数・ウィンドウ定義、calc_momentum 等のメソッド設計を含む）。
    - 設計方針として「DuckDB + SQL/Python」「データベース以外の外部 API にはアクセスしない」「(date, code) キーの dict を返す」ことを明示。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL を判定するしきい値を定義（デフォルト: 稼働率 >=99%、成功率 >=90%、送信率 >=95%、P95 <=200ms）。
    - コマンドライン引数で期間指定（--from, --to）と DB パス指定（--db）をサポート。
    - DB が存在しない場合やテーブルがない場合のフォールバック処理を実装。

- 監視用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの存在を保証（冪等操作）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / ドキュメント的注意
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる点に注意。
- LOG_DIR の作成に失敗するとファイル出力が無効化され、コンソール出力のみで継続する実装になっています。
- PAPER_FILL_MODE の値は厳密に検証され、不正値は ValueError を投げます。
- run_monitoring は MONITOR_POLL_INTERVAL に不正値が設定されている場合に警告を出しデフォルトへフォールバックします。
- 一部モジュール（research/factor_research.py）は計算ロジックの骨格が含まれており、今後の拡張で完全実装される予定です。

今後の予定（例）
- factor_research の完全実装（各ファクター算出ロジックとテスト）
- ExecutionEngine / SystemMonitor 周りの統合テスト・運用監視強化
- 銘柄別 lot_size 対応（stocks マスタの導入）などポートフォリオ設計の拡張

---
この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はパッケージのリリース日付や追加の詳細（既知の制限、マイグレーション手順等）を追記してください。