# Changelog

すべての変更点は「Keep a Changelog」形式に従って記載しています。

## [Unreleased]

### Added
- 監視プロセス起動スクリプトを追加
  - src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止制御はプロジェクト直下の data/stop_requested.flag を参照。
  - SystemMonitor を利用して単発チェックを実行し、例外はログに残して次ポーリングへ継続。
  - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用。

- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory により本番/モックブローカーを切替可能。
  - エンジンの PID 管理（data/execution.pid）、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - スレッドでエンジンを起動し、停止フラグ検知で engine.stop() を呼び安全に終了。

- 環境設定管理を追加・強化
  - src/kabusys/config.py
  - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）を実装。
  - .env/.env.local の読み込み順と OS 環境変数保護（protected keys）に対応。
  - export KEY=val、クォート文字列、インラインコメントの扱いを考慮したパーサを実装。
  - Settings クラスを導入し、J-Quants / kabu API / LINE / DB / 監視 / システム設定などのプロパティを提供。
  - Paper Trading 向けの PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH の設定をサポート。
  - KABUSYS_ENV のバリデーション（development, paper_trading, live）や LOG_LEVEL バリデーションを導入。

- 設定検証 CLI を追加
  - src/kabusys/validate_config.py
  - .env および config/*.yaml の存在や基本的な整合性チェックを実行。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML なしの場合の警告出力、KABUSYS_ENV=live 時の追加ガードなどを実装。
  - --strict オプションで警告を FAIL 扱いにできる。

- 環境設定ウィザードを追加
  - src/kabusys/config_setup.py
  - 対話式に .env を作成・更新するウィザードを提供。既存値の読み込み、シークレットのマスク表示、デフォルト値提示、保存確認を実装。

- Paper Trading 検証レポート生成ツールを追加
  - src/kabusys/tools/paper_verification_report.py
  - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み取り、システム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出してレポートを出力。
  - デフォルトの合格基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）し、PASS/FAIL 判定を行う。
  - 日付フィルタ（--from / --to）に対応。

- ポートフォリオ構築モジュールを追加
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
    - lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap のスケーリングを実装。
    - 価格欠損時のスキップ、残差の扱い（fractional remainder による追加配分）を考慮。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap：既存保有と当日売却予定を考慮して候補を除外。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはフォールバックして警告）。
  - パッケージエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- ログ設定ユーティリティを追加
  - src/kabusys/utils/logging_setup.py
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
  - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
  - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度 / CPU affinity ユーティリティを追加
  - src/kabusys/utils/process_priority.py
  - set_process_priority(level) により Windows / POSIX に対応した優先度設定を行う（失敗時は警告でスキップ）。
  - set_cpu_affinity(cpu_count) により最初の N コアにピン留め可能（例外や権限不足は警告でスキップ）。

- 研究用ファクター計算モジュールを追加（途中実装）
  - src/kabusys/research/factor_research.py
  - Momentum, Value, Volatility, Liquidity 等のファクター計算方針を実装する設計（DuckDB 接続を受け取り prices_daily / raw_financials を参照する想定）。
  - 設定された期間・ウィンドウ定数（1M/3M/6M、MA200、ATR20 等）を定義。実装の一部が未完（末尾で途中）。

### Changed
- パッケージ初期化とバージョン定義を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Fixed
- .env の読み込みで既存 OS 環境変数を保護する挙動を明確化（protected 引数）。
- ログハンドラの二重設定を防ぐため、既存ハンドラを flush/close してから削除する実装に。

---

## [0.1.0] - 2026-04-23

初回リリース。上記の機能群をまとめて公開。

### Added
- 監視・実行の起動スクリプト（run_monitoring, run_execution）。
- 環境変数管理（.env 自動読み込み、パーサ、Settings クラス）。
- 設定ウィザード（config_setup）と検証ツール（validate_config）。
- Paper Trading 検証レポートツール（tools/paper_verification_report）。
- ポートフォリオ構築ライブラリ（portfolio モジュール: 候補選定、配分、ポジションサイズ、リスク調整）。
- ログ設定ユーティリティとプロセス優先度ユーティリティ（utils）。
- 研究用ファクター計算の雛形（research/factor_research）。
- パッケージメタ情報（__version__）。

### Changed
- 初期リリースのため該当なし（新規実装）。

### Fixed
- 初期リリースのため該当なし（実装内での保護・警告挙動等を整備）。

---

注意:
- 上記は提示されたコードベースから推測してまとめた変更履歴です。実際のコミット履歴や過去リリースとの差分がある場合は、該当履歴に基づいて調整してください。