# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。KabuSys の基本機能セットを実装しました。主な追加点を以下に記載します。

### Added
- パッケージ初期版を公開（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、専用のペーパートレーディング用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory を用いたブローカークライアント生成を追加（paper/live 環境に応じたクライアント選択を想定）。
    - エンジンはデーモンスレッドで実行し、data/stop_requested.flag によるグレースフルシャットダウンをサポート。PID ファイル管理（data/execution.pid）を行う。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトへフォールバックし、警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する（監視 DB は本番 DB を参照する設計）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env パーサを強化（export 形式対応、クォート内バックスラッシュエスケープ処理、インラインコメント処理など）。
    - Settings クラスを提供し、環境変数をラップして型変換や検証（有効値チェック、デフォルト値）を行うプロパティを追加。
    - Paper Trading 用パス、各種しきい値、KABUSYS_ENV / LOG_LEVEL の検証などを含む。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 入力ガイド、シークレットマスク、保存確認、テンプレート書き出し機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML ファイルの存在・パースチェック（PyYAML が無い場合はスキップ）などを実施。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR / app_name による設定、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を設定する set_cpu_affinity 関数を追加（指定なしは何もしない）。権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全てゼロの場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（sell_codes を考慮し、"unknown" セクターは除外しない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear マップ、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装。allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer（スリッページ・手数料見積）を考慮した保守的な計算を行う。
    - 価格欠損時のスキップ、残余キャッシュを用いた端数処理（lot 単位で追加配分）などのロジックを実装。

- データ解析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計して、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを出力。
    - デフォルトの評価基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義し、Pass/Fail を判定して人間向けレポートを出力。
  - research/factor_research.py（初期実装）
    - DuckDB 接続を受け取り、prices_daily/raw_financials を使ったファクター計算（Momentum / Value / Volatility / Liquidity）を設計。モメンタム計算等の実装方針と定数を含む。

- DB 接続
  - SQLite（監視 / execution / paper_trading 用）および DuckDB（分析用）への接続処理を各起動スクリプトで統合。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサの堅牢化（引用符・エスケープ・export 形式・コメント処理の改善）。
- ログディレクトリ作成失敗時にプログラムがクラッシュしないようハンドリングを追加（ファイル出力をスキップしてコンソール出力のみ継続）。

### Security
- .env ファイルの生成時に注意喚起コメントを追加（.env をコミットしないよう明示）。

### Notes / Implementation details
- run_monitoring は監視の性質上、環境変数にかかわらず Settings.sqlite_path を使用して監視データを記録します（監視 DB は本番 DB を想定）。run_execution は KABUSYS_ENV に応じて paper_sqlite_path を使い分けます（本番 DB とペーパートレード DB の分離）。
- 多くの箇所で外部ライブラリの有無（psutil, duckdb, yaml）に依存するため、テスト環境や開発環境では環境の違いに応じたフォールバック処理を用意しています。
- research/factor_research.py ファイルは設計方針とモジュール骨子を含みます。詳細実装は継続して整備予定です。

---

今後の予定:
- strategy / execution 本体ロジック（Engine 内部、OrderManager の詳細、Reconciler 等）の単体テスト整備。
- research モジュールの完全実装とユニットテスト。
- config/*.yaml を用いた設定読み込みの実装強化およびサンプル生成スクリプトの追加。