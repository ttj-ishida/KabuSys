# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、ソースコードの現在の状態（初回リリース相当）から推定して作成されています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報を追加
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 環境設定周り
  - 環境変数と .env ファイルの自動読み込み・管理機能を追加（`src/kabusys/config.py`）。
    - プロジェクトルート検出（`.git` または `pyproject.toml`）に基づく自動ロード。
    - `.env` / `.env.local` の読み込み順序、OS環境変数保護、読み込みスキップ用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
    - `.env` の行パーサは `export KEY=val` 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - 各種設定値を取得する `Settings` クラスを提供（J-Quants / kabu API / DB パス / 監視しきい値 / 環境種別など）。
    - `PAPER_FILL_MODE` の検証、`KABUSYS_ENV` / `LOG_LEVEL` の許容値検査、`paper_sqlite_path` 等の専用設定をサポート。

- 環境設定ウィザード CLI
  - 対話式 `.env` 作成・更新ツールを追加（`src/kabusys/config_setup.py`）。
    - 多数の設定項目（実行環境、API トークン、DB パス、ログレベル、Kill Switch 振る舞いなど）を対話的に編集可能。
    - 既存 `.env` の読み込み、シークレット項目のマスク表示、保存確認を実装。

- 設定検証 CLI
  - 起動前設定チェックツールを追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数の存在確認、プレースホルダ検出、KABUSYS_ENV・LOG_LEVEL の妥当性検査。
    - DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在・YAML パース検証（PyYAML 未インストール時は警告）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行エンジン起動スクリプト
  - 実行エンジン起動ロジックを追加（`src/kabusys/run_execution.py`）。
    - `Settings` に基づく DB 接続（`paper_trading` は専用 SQLite を使用して本番 DB と分離）。
    - Broker クライアントのファクトリ利用（`BrokerClientFactory`）、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て。
    - `RiskConfig` のデフォルト値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20 等）を定義。
    - デモ用の `paper_trading` と本番分離、停止フラグ `data/stop_requested.flag` と PID ファイル `data/execution.pid` の扱いを実装。
    - エンジンはデーモンスレッドで実行され、停止フラグ検知で安全に停止。

- 監視（Monitoring）起動スクリプト
  - システム監視のポーリングループを起動するスクリプトを追加（`src/kabusys/run_monitoring.py`）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイルでループ停止。例外発生時もログを出力してループ継続。

- 監視 DB 初期化ユーティリティ
  - 監視テーブルの存在保証を行う `init_monitoring_db` 呼び出しが両スクリプトで行われる（冪等な初期化を想定）。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（`src/kabusys/utils/logging_setup.py`）。
    - stdout ストリームと日次ローテートのファイルハンドラ（デフォルト logs/、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を提供し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（`src/kabusys/utils/process_priority.py`）。
    - Windows / POSIX を吸収して `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(cpu_count)` を提供。
    - psutil を用い、権限不足や未対応環境では警告を出してスキップする安全な実装。

- ポートフォリオ構築ライブラリ
  - 候補選定・重み付け・リスク調整・株数決定の純粋関数群を追加（`src/kabusys/portfolio/*`）。
    - portfolio_builder:
      - `select_candidates`（スコア降順・タイブレーク処理）、`calc_equal_weights`、`calc_score_weights`（スコア合計 0 の際は等金額にフォールバック）を実装。
    - risk_adjustment:
      - `apply_sector_cap`（セクターごとの既存エクスポージャー計算と候補除外、"unknown" セクターは除外対象外）を実装。
      - `calc_regime_multiplier`（"bull"/"neutral"/"bear" による投下資金乗数の決定、未知レジームはフォールバックと警告）。
    - position_sizing:
      - `calc_position_sizes`（`risk_based` / `equal` / `score` の配分方法を実装）。
      - lotsize 単位切り捨て、per-stock 上限、aggregate cap（利用可能現金を超える場合はスケールダウン）および残差に基づく追加配分ロジックを実装。
      - cost_buffer を考慮して保守的にコスト見積り。

- ペーパートレード検証レポートツール
  - ペーパートレード用 SQLite を解析してレポートを生成する CLI ツールを追加（`src/kabusys/tools/paper_verification_report.py`）。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - 基準値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を実装。
    - DB パスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db` で指定可能。

- リサーチ用ファクター計算モジュール（開始）
  - ファクター計算のためのモジュールを追加（`src/kabusys/research/factor_research.py`）。
    - Momentum / Value / Volatility / Liquidity に関する設計方針と定数を定義。
    - DuckDB 接続を受け取り `prices_daily` / `raw_financials` を参照する設計。`calc_momentum` 関数の定義が始まっている（将来的にファクター計算を提供）。

### Changed
- なし（初回リリース相当の追加が中心のため、変更履歴は無し）。

### Fixed
- なし（リファクタやバグ修正の痕跡はコードからは推定できませんでした）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注意・補足:
- run_monitoring が「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明示している点、run_execution が `paper_trading` 環境で専用 DB を使用して本番 DB と完全に分離する挙動は重要な設計です。デプロイ時は `.env` の `KABUSYS_ENV` 値と各 DB パス設定に注意してください。
- ロギング・プロセス優先度設定やファイル入出力は権限や環境依存で例外になる可能性があり、例外時は警告を出してフォールバックする実装になっています。
- この CHANGELOG は与えられたソースの内容から推定して生成したもので、実際のリリースノートと差異がある可能性があります。必要であれば、差分やリリース日、著者等の情報を指定してください。