# Changelog

すべての著しい変更点は Keep a Changelog の原則に従って記録します。  
このファイルは日本語で記載されています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- 特になし（初回リリースは 0.1.0 を参照してください）。

## [0.1.0] - 2026-04-23

初回公開リリース。KabuSys の基本的な実行・監視・設定管理・ポートフォリオ構築・ユーティリティ群を実装しています。

### Added
- 全体
  - パッケージバージョンを設定: `__version__ = "0.1.0"`。
  - DuckDB と SQLite を併用するデータ基盤を導入（デフォルトパスは `data/kabusys.duckdb` / `data/monitoring.db`）。
  - プロジェクトルート自動検出および .env 自動読み込み実装（`.env` / `.env.local`、OS環境変数の保護対応）。

- 設定・CLI
  - `kabusys.config.Settings` クラスを追加し、環境変数から各種設定を取得・検証する（`KABUSYS_ENV`、DBパス、ログレベル、Paper Trading 設定など）。
  - .env ファイルを対話的に作成・更新するウィザード `kabusys.config_setup` を実装（`python -m kabusys.config_setup`）。
  - 起動前に設定の妥当性を検証する `kabusys.validate_config` CLI を実装（`python -m kabusys.validate_config`、`--strict` オプション対応）。検証対象:
    - 必須環境変数 (`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`) の有無とプレースホルダ検出
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性
    - DB パスの親ディレクトリ存在チェック
    - `config/*.yaml` の存在確認および PyYAML があればパース検証
    - 本番環境（live）向けの追加ガード（LINE 設定や Kill Switch の自動クリア警告）

- 実行エンジン
  - `run_execution.py` を実装。起動フロー:
    - ログ設定、プロセス優先度を設定（`high`）
    - `Settings` を使用して SQLite / DuckDB に接続
    - `BrokerClientFactory` によるブローカークライアント生成（`KABUSYS_ENV=paper_trading` 時は Paper 専用 DB と MockBroker を想定）
    - `OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み立て、`ExecutionEngine` をスレッドで実行
    - 停止フラグ（`data/stop_requested.flag`）および PID ファイル管理
    - Paper Trading 用 DB が本番 DB と分離される挙動をサポート（`PAPER_TRADING_SQLITE_PATH`）

- 監視
  - `run_monitoring.py` を実装。起動フロー:
    - ログ設定、プロセス優先度を設定（`high`）
    - 監視は環境にかかわらず本番 `sqlite_path` を使用して監視テーブルを初期化
    - `SystemMonitor` のポーリングループを実行。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能
    - 停止フラグ（`data/stop_requested.flag`）でループを抜ける

- ポートフォリオ構築（純粋関数）
  - `kabusys.portfolio.portfolio_builder`:
    - `select_candidates`: スコア降順＋タイブレークで銘柄候補を選択
    - `calc_equal_weights` / `calc_score_weights`: 重み計算（スコア全0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap`: セクター集中を検出し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）
    - `calc_regime_multiplier`: マーケットレジームに基づく投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告の上 1.0 にフォールバック
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes`: 等配分 / スコア配分 / リスクベース配分に対応して発注株数を計算。単元株（lot_size）で丸め、全体の投資上限（available_cash）を超える場合はスケールダウンして端数を再配分するロジックを実装
    - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, cost_buffer 等）により制約を適用

- ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定
    - LOG_DIR 作成に失敗した場合はファイル出力を無効化してコンソールのみにフォールバック
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト
  - `kabusys.utils.process_priority`:
    - `set_process_priority`：Windows/Linux/macOS の差分を吸収してプロセス優先度を設定（失敗時は警告ログ）
    - `set_cpu_affinity`：先頭 N コアにピン留め（未サポート環境ではスキップ）
  - .env パーサ:
    - `export KEY=val` 形式、クォート／エスケープ、インラインコメントの扱い、保護された OS 環境変数の上書き回避など堅牢に実装

- レポート・解析ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` または引数 `--db`）から各種指標を集計して検証レポートを出力
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（平均・最大・P95）
    - Pass/Fail 基準を定義（例: 稼働率 >= 99%、fill_rate >= 90%、P95 <= 200 ms など）
    - P95 計算をサポートし、データがない場合は N/A を表示

- 研究用基盤
  - `kabusys.research.factor_research` の骨格を追加。DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計（Momentum の計算用定数や方針が実装済み、一部関数は実装途中）。

### Changed
- 初期リリースのため変更履歴はありません（新規追加が中心）。

### Fixed
- 初期リリースのため修正履歴はありません。

### Removed
- 該当なし

### Security
- 環境変数の取り扱いにおいて .env は Git にコミットしないことをドキュメントで明記（`config_setup` に注意書きあり）。

## 注意事項 / 既知の制限（備考）
- apply_sector_cap:
  - price_map における価格欠損（0.0）の扱いに関する TODO コメントあり（将来的に前日終値等でフォールバックする予定）。
- position_sizing:
  - lot_size は現状グローバル定義（全銘柄共通）。将来的に銘柄別 lot_size をサポートする設計拡張がコメントに記載されている。
- research/factor_research:
  - 一部関数（ファイル末尾にかけて）が未完了または続きがある状態。追加実装が必要。
- ログディレクトリ作成やプロセス優先度設定、CPU affinity 設定は OS 権限や環境に依存し、失敗時は警告を出して処理を継続する挙動です。
- Paper Trading 環境は MockBrokerClient を想定した分離 DB を使用する設計だが、実際の MockBroker 実装や振る舞いの詳細は別モジュールに依存します。

---

訳注: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴や変更点に基づく公式な CHANGELOG を作成する場合は、Git の履歴を参照してください。