# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
（注: 以下はリポジトリ内のソースコードから推測して作成した初期リリース向けの変更履歴です。）

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = 0.1.0）。
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - ブローカークライアント生成を BrokerClientFactory 経由で抽象化。
    - paper_trading 環境では専用の paper_trading DB を使用して本番 DB と分離。
    - 実行中は PID ファイルを扱い、stop フラグ (data/stop_requested.flag) によって安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
- 監視用エントリスクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグでループを終了、KeyboardInterrupt もハンドリング。
- 設定管理
  - config.py: 環境変数読み込み・ラッパー（Settings クラス）を追加。
    - 自動 .env ロード機能（.env, .env.local）を備え、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - 必須/任意の各種設定プロパティを整理（J-Quants / kabuAPI / LINE / DB / 監視 / システム設定 等）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等の取り扱いを実装。
- 設定ウィザード & 検証ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env 読み込み・編集に対応し、テンプレート書き出しを行う。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・パス・YAML ファイルの存在・本番用ガードをチェック。--strict オプションで警告を fail 扱いにできる。
- ロギングユーティリティ
  - utils/logging_setup.py を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による設定や既存ハンドラの安全なリセットに対応。
- プロセス優先度ユーティリティ
  - utils/process_priority.py を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
    - 権限不足や未対応 OS 時は警告を出して安全にフォールバック。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates, calc_equal_weights, calc_score_weights を追加（スコアに基づく選定・重み付け）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限）および calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各 allocation_method に対応した株数決定ロジックを追加。
    - 単元株丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリング）等を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - paper_trading の SQLite DB（デフォルト data/paper_trading.db）から指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など）を集計して報告を出力。
    - PASS/FAIL 判定および閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。
- リサーチ（ファクター計算）基盤
  - research/factor_research.py を追加（モメンタム / Value / Volatility / Liquidity に関する設計とモジュール骨組み）。
    - DuckDB を用いた prices_daily / raw_financials 参照を想定した設計（calc_momentum 等の実装を開始）。

### 変更 (Changed)
- ログ出力のポリシー
  - 全体で stdout を優先する設計へ（cron等でのリダイレクト運用を考慮）。
  - ファイル出力に失敗した場合はコンソール出力のみで継続する堅牢化を実施。
- DB 周りの扱い
  - 監視（monitoring）では環境に関係なく本番 sqlite_path を使用する仕様に明示的に統一。
  - 実行エンジンでは paper_trading 環境用に専用 DB を分離（settings.is_paper 判定）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - config._parse_env_line でクォート付き値のエスケープ処理、インラインコメントの扱い、export プレフィックス対応などを実装し .env の取り扱いを改善。
- 起動時の安全措置
  - 実行・監視スクリプトで stop フラグを確認して安全に起動/停止する仕組みを追加。
  - run_execution の起動前に stop フラグが立っている場合は起動せず終了する処理を追加。

### 注意点 / 既知の制約 (Known issues)
- research/factor_research.calc_momentum の実装が途中で切れており、ファクター計算の完全実装は引き続き必要。
- position_sizing の一部（価格欠損時のフォールバック等）は TODO コメントあり。価格欠損があるとエクスポージャー評価が過小になる可能性あり。
- 一部機能は外部依存（psutil, duckdb, PyYAML 等）に依存しており、未インストール時は機能制限や警告が発生する（validate_config や logging_setup はそれぞれ該当箇所でフォールバックを行う）。

---

今後の予定（推測）
- factor_research の完成（全ファクターの実装と正規化ユーティリティの統合）。
- ExecutionEngine / Monitoring の詳細なテストと運用用ドキュメント整備。
- 単体テストの追加および CI ワークフロー整備。

もし CHANGELOG に追加したい詳細（例えばリリース日や強調したい変更点）があればお知らせください。