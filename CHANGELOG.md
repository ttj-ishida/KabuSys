# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17
初期リリース。

### Added
- 全体
  - 初回リリースとして自動売買システム KabuSys の基本コンポーネントを追加。
  - バージョンは `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ開始スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視はどの KABUSYS_ENV でも本番用の sqlite_path を使用して監視テーブルを初期化。
    - stop フラグファイル (data/stop_requested.flag) による柔軟な停止検出を実装。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite DB（`data/paper_trading.db` デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全な起動・停止制御。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。

- 設定管理
  - config.py
    - 環境変数読み込み・管理用の `Settings` クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env の自動読み込み（`.env` → `.env.local` の順、既存 OS 環境変数を保護）。
    - 複数の設定値をプロパティとして提供（DB パス、API トークン、監視しきい値、環境種別判定、paper_trading 用パスなど）。
    - `.env` の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` の導入。
    - `.paper_fill_mode` の入力検証（有効値チェック）や各種しきい値の float パース等を実装。

  - config_setup.py
    - .env 初期作成/更新のための対話式ウィザードを追加。
    - デフォルト値・選択肢・マスク表示（secret）に対応し、最終確認後に .env を生成。
    - 生成された .env に対する注意（Git にコミットしない等）を出力。

  - validate_config.py
    - 起動前検証 CLI を追加。`.env` と `config/*.yaml` の存在・基本妥当性を検査。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が存在する場合）。
    - `--strict` オプションにより警告を Fail 扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、タイブレークに signal_rank）を行う `select_candidates` を追加。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を追加。全スコアが 0 の場合は等金額にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を実施する `apply_sector_cap` を追加（売却予定銘柄の除外対応、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear を想定し、未知レジームは警告後にフォールバック 1.0）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する `calc_position_sizes` を追加。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - aggregate cap 超過時のスケールダウン処理（端数分配は remainder による公平配分）や cost_buffer による保守的見積りを実装。
    - 価格欠損時のスキップとログ出力に対応。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を吸収。
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。権限不足や未対応 OS 時は警告を出力してスキップ。

- 研究（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を用いたファクター計算モジュールを追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、相対 ATR、20日平均出来高等）等を計算する関数を用意。
    - DuckDB のウィンドウ関数を利用して効率的に計算、データ不足時は None を返す設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - SQLite（paper_trading DB）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

Notes / Known limitations
- .env の自動読み込みはプロジェクトルートが見つからない場合や `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されている場合はスキップされます。CI や配布環境での挙動に注意してください。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別対応を想定）。
- research/factor_research は DuckDB 上のテーブル（prices_daily / raw_financials）に依存します。テーブルが存在しない場合は例外が発生する可能性があります（テスト・運用前にデータ準備を推奨）。
- process_priority の設定は OS 権限に依存します。権限不足時は警告ログを出して処理を続行します。

もし詳細なリリースノート（ファイルごとの変更差分や開発上の設計メモ）が必要であれば、その旨を教えてください。追加で作成します。