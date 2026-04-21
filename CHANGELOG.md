# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21
初回リリース — KabuSys のコア機能を実装しました。主な追加点、動作仕様、重要な環境変数・デフォルトを以下にまとめます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視動作では実行環境にかかわらず本番用の SQLite（`Settings.sqlite_path`）を使用する旨の実装。
    - データディレクトリ内の `stop_requested.flag` を検知して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用いペーパートレード専用 DB (`PAPER_TRADING_SQLITE_PATH` / デフォルト: data/paper_trading.db) を使用して本番 DB と分離。
    - PID ファイル (`data/execution.pid`) の取り扱い、`stop_requested.flag` による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・検証・ウィザード
  - config.py
    - 環境変数の自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - `.env` と `.env.local` の読み込み順をサポート。OS 環境変数は保護される（上書きされない）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - `Settings` クラスを導入し、J-Quants / kabu API / DB パス /監視閾値 等の取得ラッパーを提供。値検証（例: `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL`）を実装。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。項目定義・既存値の読み取り・マスク表示等を実装。
  - validate_config.py
    - 起動前に `.env` と config/*.yaml の検証を行う CLI を追加。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML 未インストール時はスキップ）などを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、タイブレークに signal_rank）と候補上位 N 選定を実装。
    - 等配分（equal）およびスコア加重（score）で重みを計算。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限（apply_sector_cap）を実装。既存ポジションのセクター別時価を評価し、上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め（lot_size、デフォルト 100）、銘柄ごとの上限（max_position_pct）や総投下上限（max_utilization）を考慮。
    - aggregate cap 超過時のスケーリング、残余キャッシュを用いた端数ロジック（fractional remainder による追加配分）を実装。
    - 手数料・スリッページ想定のための cost_buffer を考慮。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。Stdout への StreamHandler（stdout を使用）と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）を設定。
    - 既存ハンドラをクリアして重複登録を防止。環境変数 `LOG_LEVEL`, `LOG_DIR` を尊重。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows の優先度クラスと POSIX の nice 値を吸収し、プラットフォーム非依存の呼び出しを提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足時は警告でスキップ）。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime%）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計。
    - 基準値（デフォルト）: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms。
    - 日付レンジ指定（--from / --to）と DB 指定（--db / 環境変数）をサポート。
    - SQLite のテーブル未存在やデータ不足に対するフォールバックを実装。

- 研究用モジュール（骨組み）
  - research/factor_research.py
    - DuckDB を用いたファクター計算の骨組みを追加（モメンタム、MA200、ATR、流動性等を想定）。関数定義と定数類を用意。実装の一部が未完（ファイル末尾で切れている）。

- パッケージ情報
  - __init__.py にてバージョン `0.1.0` を設定。

### Changed
- 環境変数の読み込みロジック
  - `.env` のパースでクォート、エスケープ、インラインコメントの扱いを強化。
  - `export KEY=val` 形式に対応。
  - 自動ロードはプロジェクトルートの存在確認（.git または pyproject.toml）に依存するため、配布後の環境でも CWD に依存せず動作する設計。

- ロギングの既定動作
  - stdout を標準出力に使い、cron 等から stdout/stderr を一括リダイレクトしやすくした。

### Fixed
- （リリース時点で既知のバグ修正項目はありません）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

備考:
- 実際の運用前には validate_config の実行を推奨します（python -m kabusys.validate_config）。  
- `.env` は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きあり）。  
- process_priority / cpu_affinity は権限や OS に依存するため、失敗時は警告で続行する設計です。