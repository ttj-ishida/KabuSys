# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### 注意 / 既知の問題
- research/factor_research.py の実装が途中で終了している箇所があります（momentum 計算の途中でファイルが切れています）。本モジュールは現状スケルトン／部分実装となっており、完全なファクター計算を行うには追加実装が必要です。
- position_sizing.calc_position_sizes, risk_adjustment.apply_sector_cap 中に記載された TODO（銘柄別 lot_size の対応、価格フォールバック等）が残っています。
- ログディレクトリ作成やプロセス優先度設定等は OS 権限や環境によって警告を出してフォールバックする実装です。運用時は権限設定を確認してください。

---

## [0.1.0] - 2026-04-21

### Added
- 初期リリースを公開。パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。
- 環境設定 / 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定値（DB パス、API トークン、実行環境フラグ、監視閾値など）を取得できる。
  - 自動 `.env` ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml`）。`.env` / `.env.local` の読み込み順をサポート。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` のパース処理を強化: `export KEY=val` 形式、クォート値（シングル／ダブル）、エスケープシーケンス、行内コメントの扱いに対応。
  - 必須環境変数チェックのための `_require` ヘルパーを追加。

- CLI ツール
  - `kabusys.config_setup`：対話式の環境設定ウィザードを追加。`.env` の初期作成・更新を支援。
  - `kabusys.validate_config`：起動前に環境変数・config/*.yaml の整合性を検証する CLI を追加。`--strict` オプションで警告も失敗扱いにできる。
  - `kabusys.tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定を行う。

- 実行・監視ランナースクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、Broker クライアント生成、OrderManager/RiskManager/Reconciler の組み立て、スレッド実行と停止フラグ監視を実装。
    - `KABUSYS_ENV=paper_trading` 時は専用の Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID 管理をサポート。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。

- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：統一的なログ設定ユーティリティを追加。コンソール（stdout）用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）のファイル出力を設定。既存ハンドラの二重設定を防止、ログレベル・ログディレクトリは引数・環境変数で制御。
  - `kabusys.utils.process_priority`：プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows（HIGH_PRIORITY_CLASS 等）・POSIX（nice 値）差分を吸収。`set_process_priority(level)`、`set_cpu_affinity(n)` を提供。権限不足時は警告を出して安全にスキップする。

- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`：シグナル選定・重み付けロジックを追加。
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を使用）
    - calc_equal_weights / calc_score_weights: 等配分・スコア正規化配分を提供（全スコアが 0 の場合は等配分にフォールバックして警告）
  - `kabusys.portfolio.risk_adjustment`：セクター上限適用およびレジーム乗数計算を追加。
    - apply_sector_cap: 既存ポジションを元にセクターごとのエクスポージャーを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値はフォールバックと警告）。
  - `kabusys.portfolio.position_sizing`：株数決定ロジックを追加。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap によるスケーリング（cost_buffer を考慮）を実装。
    - スケールダウン時の端数配分ロジック（fractional remainder に基づく追加配分）を実装。

- データベース初期化ユーティリティ
  - `monitoring_db.init_monitoring_db`（参照されていることから存在）を用いて監視テーブルの初期化（冪等）が行われることを想定した起動フローを追加。

- パッケージエクスポート
  - `kabusys.portfolio.__init__` による主要関数の公開を追加（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- `.env` パーサーでの複数のエッジケースを扱うよう改善（行先頭の `export`、引用符付き値内のバックスラッシュエスケープ、インラインコメントの扱い等）。これにより .env の読み込みがより堅牢になりました。

### Deprecated
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）