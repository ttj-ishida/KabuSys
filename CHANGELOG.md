# Changelog

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

注: バージョンはパッケージの __version__ に合わせて初期リリースを 0.1.0 としています。

## [0.1.0] - 2026-04-19

初期リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てを実施。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag の存在で安全に停止する仕組みを搭載（実行中は data/execution.pid を使用）。
    - RiskManager の初期設定（デフォルト値: max_position_pct 等）をコード内に定義。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告を出してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用する仕様。
    - duckdb 接続を確立して SystemMonitor を初期化、定期的に monitor.check_once() を呼び出す。
    - data/stop_requested.flag の検知や KeyboardInterrupt による終了処理を実装。

- 環境設定と検証
  - config.py: 環境変数/ .env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local の自動ロード（OS 環境変数を保護、.env.local は override=True）。
    - .env の行パースは export プレフィックス、クォート、エスケープ、インラインコメントをサポート。
    - Settings に多数のプロパティを公開（J-Quants・kabu API・DB パス・paper_trading の挙動・監視閾値・環境判定等）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。

  - config_setup.py: インタラクティブな .env ウィザードを実装。
    - 対話式で .env の作成・更新を支援。シークレット項目はマスク表示。
    - デフォルト値 / 選択肢を提示。最終確認後に .env を書き出す。

  - validate_config.py: 起動前設定検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告など。
    - --strict モードで警告を FAIL 扱い（exit(1)）にできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。タイブレークは signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分の実装。全銘柄スコアが 0 の場合は等配分へフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別上限（max_sector_pct）を評価して過剰セクターに属する候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" | "equal" | "score"）に基づいて発注株数を計算。lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を使った保守的コスト見積り、端数配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通のロギング設定ユーティリティを実装。StreamHandler を stdout に設定し、TimedRotatingFileHandler（日次ローテーション・30日保持）を使用。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数でレベルや出力先を解決可能。既存ハンドラは上書き（重複防止）する。

  - utils/process_priority.py:
    - プラットフォーム差分を吸収してプロセス優先度（nice / Windows 優先度クラス）と CPU affinity を設定するユーティリティを追加。
    - サポートされない OS や権限不足時は警告を出して安全にスキップ。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を集計し、閾値に基づいて PASS/FAIL を判定。
    - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を参照。

- 研究モジュール（未完の箇所あり）
  - research/factor_research.py（フォーマットおよび骨子を追加）
    - DuckDB を用いたモメンタム・ボラティリティ等のファクター計算設計を含む（関数 calc_momentum の実装開始。ファイル末尾は断片的に終わっています）。

### Changed
- ロギングの挙動
  - 全体のログ設定は utils.logging_setup.setup_logging に一元化され、起動スクリプトはそれを利用して統一的にログを構成するように変更（Stream は stdout を使用）。

### Fixed
- .env 読み込みの堅牢化
  - .env のパースで export prefix、クォート付き値のエスケープ処理、インラインコメントの扱いを細かく実装し、実運用での誤読を軽減。

### Notes / Implementation details
- 自動 .env ロードはデフォルトで有効だが、テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することでスキップできる。
- MONITOR_POLL_INTERVAL: 環境変数が不正（非整数や 0 以下）の場合は警告を出してデフォルト 60 秒にフォールバックする。
- Logging ファイルハンドラ作成に失敗した場合でもコンソール出力は継続されるため、起動失敗のリスクを低くしている。
- process_priority、set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告を出して続行する（安全性重視）。
- portfolio モジュールの関数群は副作用を持たない純粋関数として設計されており、ユニットテストが容易な構造。

---

今後の予定（例）
- research/factor_research.py の完全実装（ファクター計算ロジックの完成）。
- ExecutionEngine / SystemMonitor 等の統合テストとドキュメント充実。
- 個別銘柄の lot_size を銘柄マスタから取得する対応（position_sizing の拡張）。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py 相当）の追加。

もし特定の変更点について詳細な記載順序や追加の項目（Breaking changes やマイグレーション手順など）が必要であれば指示してください。