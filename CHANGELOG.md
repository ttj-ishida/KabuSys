CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に従います。  
タグ付け規約: Semantic Versioning。日付はコードベースから推測して付与しています。

Unreleased
----------

（現状なし）

0.1.0 - 2026-04-25
-----------------

Added
- 全体
  - 初回リリース。KabuSys 日本株自動売買システムの基本モジュールを追加。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV による paper_trading モードのサポート（MockBrokerClient 使用、paper_trading 専用 SQLite を利用して本番 DB と分離）。
    - ExecutionEngine をバックグラウンドスレッドで実行し、data/stop_requested.flag による安全な停止処理を実装。
    - プロセス優先度を起動直後に "high" に設定。
    - DuckDB および SQLite 接続の初期化（監視テーブルの冪等初期化を含む）。
    - RiskManager / Reconciler / OrderManager 等の依存コンポーネント組み立てとデフォルト設定（例: リスク設定の既定値）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データを一元化）。
    - 停止フラグ file（data/stop_requested.flag）を検出してループを終了。
    - 例外発生時はログに残して次のポーリングへ継続（堅牢化）。

- 設定・検証・セットアップ
  - config.py: 環境変数管理モジュールを追加。
    - .env 自動読み込み（プロジェクトルートの判定: .git または pyproject.toml を探索）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - export KEY=val 形式、クォート文字列（バックスラッシュエスケープ対応）、行内コメントの取り扱いなど堅牢な .env パーサを実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / monitoring / モード判定など）と入力検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
    - Settings クラスとグローバル settings インスタンスを提供。

  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期作成・更新を支援。シークレット項目はマスク表示、デフォルト・選択肢・説明を付与。
    - .env を生成・上書きする機能を持ち、保存前に確認プロンプトを表示。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなどを実装。
    - --strict オプションで警告も失敗（exit(1)）扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - コンソール（stdout）への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラの二重設定防止（クリアして再設定）。ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルとログディレクトリの解決順を定義（引数、環境変数、デフォルト）。

  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を吸収するクロスプラットフォーム実装。
    - set_process_priority(level) により high/normal/low を設定（権限不足などは警告でスキップ）。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定（未対応 OS や権限不足は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を提供。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用。既存ポジションに基づきセクターのエクスポージャーを算出し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear に対応、未知値は警告と 1.0 フォールバック）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 重みやリスクベースでの発注株数決定ロジックを実装。
      - risk_based / equal / score の割当方式に対応。
      - 単元株（lot）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン（コストバッファ考慮）、端数処理で残余キャッシュを用いた追加割当のアルゴリズムを含む。
      - 価格欠損や zero 価格を検知してスキップする堅牢性。

- リサーチ・ファクター計算
  - research/factor_research.py:
    - Momentum 等のファクター計算モジュールを追加（設計・定数・calc_momentum のスケルトン含む）。DuckDB の prices_daily / raw_financials テーブルを前提にした設計方針。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値判定（稼働率 >= 99%、fill >= 90% 等）で PASS/FAIL を出力。
    - 日付フィルタ（--from/--to）サポート、DB パスは引数／環境変数で指定可能、DB 不存在やテーブル欠落時にフォールバックして堅牢に動作。

Changed
- .env のパースと読み込み挙動を堅牢化
  - export プレフィックス対応、クォート値のエスケープ解釈、行内コメントの取り扱い、既存 OS 環境変数を保護する protected オプションを実装。

Fixed
- なし（初回リリースに含まれる既存実装の堅牢化・例外処理の追加を記載）。

Security
- シークレット値は対話式 UI 表示時にマスク表示（config_setup.py）。
- .env の生成コメントで Git 管理しない注意喚起を記載。

Notes / 注意事項
- run_monitoring は監視データ用に settings.sqlite_path（production と想定）を使用する設計になっており、環境に応じた分離が必要な場合は設定を見直してください。
- process priority / CPU affinity の設定は権限や OS に依存するため、許可がない場合は警告でスキップされます。
- research/factor_research.py はファクター計算のフレームワークを提供しますが、関数の一部（calc_momentum の実装途中など）は引き続き実装が必要です。

参考（主要ファイル）
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*
- src/kabusys/research/factor_research.py
- src/kabusys/tools/paper_verification_report.py

-- End of CHANGELOG --