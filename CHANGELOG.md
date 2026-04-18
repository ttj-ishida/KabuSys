# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載します。  
このファイルは、リポジトリの現状（ソースコードから推測）に基づいて作成された推定の変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開（コードベースの主要機能を実装）。

### Added
- 全体
  - パッケージ初期化（src/kabusys/__init__.py）を追加。バージョンを `0.1.0` に設定。
  - プロジェクトルート探索ロジックと自動 .env 読み込み機能を実装（src/kabusys/config.py）。
    - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、環境変数の取得と検証（必須変数、列挙値チェック、パス展開など）を集中管理。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）を実装。
    - 対話形式で .env を生成/更新するウィザードを提供。
    - デフォルト値、選択肢、シークレット入力対応、.env の書き込み機能を実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）を実装。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在およびパース（PyYAML がある場合）をチェック。
    - 本番環境向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START など）を追加。
    - --strict オプションで警告も失敗扱いにできる。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - ExecutionEngine の起動フローを記述（プロセス優先度設定、DB 接続、Broker クライアント生成、依存コンポーネント組み立て、スレッド実行、停止フラグ監視）。
    - Paper Trading 環境では paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）による制御。
  - 監視ポーリングスクリプト（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor を周期的に実行するポーリングループ。環境変数 MONITOR_POLL_INTERVAL による間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop flag による停止、例外時のログ出力と次ポーリング継続を実装。
  - ロギングユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定する関数を提供。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
  - プロセス優先度/CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows/Linux/macOS を吸収してプロセス優先度（high/normal/low）を設定。
    - psutil を用い、アクセス権限不足等は警告でフォールバック。
    - set_cpu_affinity によりプロセスを先頭 N コアにピンニング可能。
  - Portfolio 関連（src/kabusys/portfolio/*）
    - 候補選定と重み計算（portfolio_builder.py）
      - select_candidates: スコア降順で上位 N を選択（signal_rank をタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。スコア合計が 0 の場合は等金額配分にフォールバック。
    - セクター集中制限・レジーム乗数（risk_adjustment.py）
      - apply_sector_cap: 既存保有のセクター時価比率を計算し、閾値を超えるセクターの新規候補を除外。
      - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告のうえ 1.0 でフォールバック。
    - 株数決定・リスク制限・単元株丸め（position_sizing.py）
      - allocation_method ("risk_based" / "equal" / "score") に対応した株数計算ロジックを実装。
      - risk_based: 許容リスク / 損切り率に基づく理論株数を算出、単元で丸め、既存保有分を考慮。
      - equal/score: 重み・配分に基づいた数量算出。max_position_pct、max_utilization、lot_size、cost_buffer 等を考慮した aggregate cap のスケーリングと残差処理を実装。
    - portfolio パッケージ出口定義（__init__.py）を提供。
  - Execution コンポーネント（参照のみ、実実装は別ファイルに存在すると想定）
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager、Order 関連インターフェースを組み合わせる起動フローを実装。
    - RiskConfig と EngineConfig のデフォルトパラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）を設定。
  - 監視 DB 初期化呼び出し（init_monitoring_db を起動で冪等に実行）。
  - DuckDB を分析用 DB として利用（Settings.duckdb_path）。Execution / Monitoring 両方で接続を確保。
  - Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）を追加。
    - SQLite の paper_trading DB から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - CLI 引数で期間指定（--from/--to）と DB パス指定（--db）をサポート。

### Changed
- N/A（初回リリースのため「追加」中心の記載）

### Fixed
- N/A（初回リリース）

### Deprecated
- N/A

### Removed
- N/A

### Security
- 特になし

### Notes / Known issues
- research/factor_research.py はファイル末尾が未完（途中で切れているように見える）。ファクター計算ロジックは設計方針・定数が定義されているが、実装の一部が欠けているため追加実装が必要。
- position_sizing.py の一部に TODO コメントあり:
  - 銘柄ごとの lot_size を将来的にサポートする拡張を予定。
  - 価格（price）が欠損した場合のフォールバック処理（前日終値や取得原価など）の実装が未完。
- apply_sector_cap で "unknown" セクターは上限適用を行わない設計だが、実運用ではマスタ整備が必要。
- run_monitoring/run_execution は stop フラグや PID ファイル、各種環境変数に依存するため、デプロイ手順や運用ルールの明確化が必要。
- .env の自動ロードはプロジェクトルート判定に .git または pyproject.toml を使用するため、パッケージ配布後や特殊配置では自動ロードがスキップされる場合がある点に注意。

---

（この CHANGELOG はコードの静的解析と注釈に基づく推定です。実際のコミット履歴や変更履歴が別にある場合は、そちらを優先してください。）