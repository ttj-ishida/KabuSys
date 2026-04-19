# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初回公開リリースとして、以下の機能群を実装しています。

なお日付は本リリースの作成日です。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 全体
  - プロジェクト初期リリース。主要な起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築、検証ツールを実装。
  - バージョン定義を `src/kabusys/__init__.py` に追加（__version__ = "0.1.0"）。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを実装。
    - 起動時にプロセス優先度を設定（`utils.process_priority.set_process_priority` を使用）。
    - 環境変数 `KABUSYS_ENV` が `paper_trading` の場合は paper 用の SQLite（デフォルト `data/paper_trading.db`）を使用し、MockBrokerClient を利用して本番 DB と完全分離する挙動をサポート。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）を使用した安全停止制御を実装。
    - DuckDB 接続を行い（`settings.duckdb_path`）、監視テーブルの初期化を行う。

  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。0 以下や不正な値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境に関わらず本番用の `sqlite_path` を使用する設計（監視データの一元化）。
    - 停止フラグ（`data/stop_requested.flag`）検知によるループ終了処理、`KeyboardInterrupt` ハンドリング、例外発生時のログと継続処理を実装。

- 設定・環境管理
  - `config.py`
    - .env ファイル自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。OS 環境変数を保護しつつ `.env` / `.env.local` を読み込む。
    - 複雑な .env パース実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理など）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境フラグ等のプロパティを公開。妥当性チェック（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を内蔵。
    - `settings` のインスタンスをモジュール下でエクスポート。

  - `config_setup.py`
    - 対話式環境設定ウィザードを実装（.env の初期作成・更新に利用）。
    - 必須項目・任意項目の指定、シークレット表示マスク、デフォルト提示、.env 書き込み機能を提供。
    - 書き込みテンプレートは .env のコメント付で生成される。

  - `validate_config.py`
    - 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック（PyYAML が利用可能な場合）などを行う。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。
    - 本番環境向けの追加ガードを実装（LINE 通知設定の未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。

- ユーティリティ
  - `utils/logging_setup.py`
    - ログ初期化ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリ解決の優先順位を提供。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - `utils/process_priority.py`
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を提供。
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を実装し、権限不足や未対応 OS の場合は安全に警告を出す。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - `portfolio/portfolio_builder.py`
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分へフォールバック）を実装。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限（既存保有のセクター比率が閾値を超える場合に新規候補を除外）を実装。売却予定銘柄を除外して計算可能。
    - 市場レジームに応じた資金乗数（bull/neutral/bear）を返す関数を実装（未知レジームは 1.0 でフォールバック）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ想定）考慮、残余キャッシュを使った端数配分ロジックを実装。
  - `portfolio/__init__.py`
    - ポートフォリオ関連 API をパッケージ公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- 監視・検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用の検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs テーブルから各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95））を集計。
    - Pass/Fail 判定用の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、期間指定（--from/--to）や DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - 出力は人間可読なテキストレポート。

- リサーチ
  - `research/factor_research.py`
    - ファクター計算モジュールのスケルトンを追加（モメンタム / Value / Volatility / Liquidity 設計を明記）。
    - モメンタム計算関数（calc_momentum）の骨組みを用意（DuckDB 接続を受け取り prices_daily を参照する設計）。※実装の続きが存在（ファイル途中まで実装）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

補足:
- 多くのモジュールは「純粋関数」または依存注入パターンで実装されており、ユニットテスト・モック化が容易な設計になっています（例: DuckDB / SQLite / broker client を外部から渡す形）。
- .env の自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- Paper Trading 用 DB の分離、実行時の Kill Flag / PID 管理、日次ログローテーションなど運用面の配慮を行っています。