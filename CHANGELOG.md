# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語）

## [0.1.0] - 2026-04-18
初回リリース。KabuSys のコア CLI/ライブラリ群を実装しました。以下はコードベースから推測できる主要な機能追加・振る舞いです。

### Added
- 全体
  - パッケージ初期バージョンを設定（src/kabusys/__init__.py: `__version__ = "0.1.0"`）。
  - DuckDB / SQLite を用いたデータ保存・分析の基盤を導入（duckdb, sqlite3 を利用）。
- 実行系 / 監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて本番 DB と Paper Trading 用 DB を切り分け（`PAPER_TRADING_SQLITE_PATH` / `settings.is_paper`）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御はプロジェクトルートの `data/stop_requested.flag` を監視。エンジンは別スレッドで稼働し、フラグ検出時に安全停止。
    - 実行用 PID ファイル出力（`data/execution.pid`）に対応。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、0以下は無効扱いしてフォールバック）。
    - 監視用 DB 初期化（init_monitoring_db）と SystemMonitor による定期チェックを実行。
    - 停止フラグ（`data/stop_requested.flag`）検知で安全にループを抜ける。
    - Monitoring は KABUSYS_ENV にかかわらず設定された sqlite_path（本番 DB）を使用することが明記されている。
  - 起動時にプロセス優先度を設定（`set_process_priority("high")`）して実行（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差異を吸収する実装。
    - CPU affinity 設定ユーティリティ `set_cpu_affinity` を提供。
- 設定管理
  - 環境変数 / .env 読み込みロジックを実装（src/kabusys/config.py）。
    - プロジェクトルートを `.git` または `pyproject.toml` を起点に自動検出して `.env` / `.env.local` を読み込む（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env ファイルの行パースはクォート・エスケープ・コメント処理に対応（`export ` 形式にも対応）。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / DB パス / monitoring 閾値 / 環境判定など）。`PAPER_FILL_MODE` の検証や `KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックを行う。
    - `settings` オブジェクトをエクスポート。
  - 対話式設定ウィザードを実装（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援する CLI。複数の項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を対話的に入力・保存可能。
    - シークレット項目は表示をマスクして扱う。既存 .env を読み込んでデフォルトとして再利用。
- 設定検証
  - 起動前チェック用 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML がない場合はスキップ）など。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler（stdout 指定）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順序（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - process_priority と組み合わせて起動スクリプトから優先度を高く設定する挙動を採用。
- ポートフォリオ構築 / リスク管理
  - 銘柄選定・重み付け関数群を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - シグナルのスコア降順ソート（同点は signal_rank でブレーク）、等配分・スコア加重配分を提供。全スコアが 0 の場合は等配分へフォールバックして WARN を出力。
  - セクター集中制限・レジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - 既存保有のセクター別時価を計算し、`max_sector_pct` を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジームに応じた乗数マッピング（"bull":1.0, "neutral":0.7, "bear":0.3）。未定義レジームは警告のうえ 1.0 にフォールバック。
  - 発注株数決定ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - 複数の allocation_method をサポート（"risk_based", "equal", "score"）。
    - risk_based ではリスクベースの株数計算（risk_pct, stop_loss_pct を考慮）。
    - per-position 上限（max_position_pct）や利用上限（max_utilization）、単元株（lot_size）で丸め処理を実装。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）を導入。スケールダウン後の端数再配分ロジック（lot_size 単位、余りの大きい順）を実装。
    - コストバッファ（cost_buffer）を考慮して保守的なコスト見積りを行う。
- 解析・検証ツール
  - Paper Trading の検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite データベース（デフォルト: data/paper_trading.db）から system_status / trade_logs / risk_logs を集計し、稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを算出。
    - 閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200ms）。
    - コマンドライン引数で対象期間（--from, --to）と DB パスを指定可能。
- リサーチ（部分実装）
  - ファクター計算モジュールの骨子を追加（src/kabusys/research/factor_research.py）。
    - モメンタム / MA200 / ATR 等の定数・関数設計が記載されており、DuckDB を用いた prices_daily テーブル参照でファクターを算出する設計方針。

### Changed
- （初回リリースのため「変更」は該当なし。今後の変更はここに記載予定）

### Fixed
- （初回リリースのため「修正」は該当なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- 環境変数中のシークレットは対話ウィザードでマスク表示するなど、取り扱いに注意した設計を採用（.env を Git にコミットしない旨の注記あり）。

---

補足 / 注意点（実装から推測）
- run_monitoring が監視 DB として常に production の sqlite_path を使う点は意図的に設計されている（監視データは環境に依存しない想定）。Paper Trading 発注ログ等は別 DB に分離される（settings.paper_sqlite_path）。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や CI 環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使うかカレントディレクトリに注意が必要。
- factor_research.py はファイル末尾が途中で切れているため（本リリースでは未完の可能性あり）、完全なファクター計算実装は今後の実装対象。
- 実行環境での優先度設定や CPU affinity は権限不足により一部環境でスキップされる挙動（警告ログ）を取る設計。

---

この CHANGELOG はコードベースの状態から推測して作成しています。差分や履歴の細かな経緯は Git コミットログを元に作成するとより正確になります。必要であれば、コミット履歴を元により詳細な CHANGELOG を生成します。