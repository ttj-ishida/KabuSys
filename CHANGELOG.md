# CHANGELOG

すべての notable な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

なお、本 CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース。主に以下の機能・ユーティリティ・CLI を追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 環境設定・読み込み
  - 環境変数管理モジュール `kabusys.config` を追加。
    - プロジェクトルートを自動検出して `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - `.env` のパースは `export KEY=val`、クォート、エスケープ、インラインコメント（クォートなしでの `#` 処理）に対応。
    - 環境設定を集約する `Settings` クラスを提供（例: `sqlite_path`, `duckdb_path`, `env` の検証など）。
    - `PAPER_FILL_MODE` の値検証、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックなどを実装。
- 設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式で `.env` の作成・更新を支援。
  - デフォルト値やシークレット項目のマスク表示、既存 `.env` の読み込み、書き出し機能を実装。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。起動前に必須環境変数・DB パス・config/*.yaml の存在とパース（PyYAML があれば）を検証。
  - `--strict` オプションで警告も失敗扱いにできる。
  - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や kill flag の自動クリア設定の警告）を実装。
- 実行 / 監視ランナー
  - `kabusys.run_execution` を追加。実行エンジンの起動スクリプトを提供。
    - `KABUSYS_ENV=paper_trading` 時は paper 用 SQLite を使用して本番 DB と分離。
    - Broker クライアント生成、OrderRepository、OrderManager、RiskManager（デフォルト設定を含む）、Reconciler、ExecutionEngine の組み立てと起動／停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルに対応。
    - プロセス優先度を起動時に設定（`set_process_priority("high")`）。
  - `kabusys.run_monitoring` を追加。SystemMonitor のポーリングループを実装。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の `sqlite_path` を使用する（環境に依らず監視 DB を共通利用）。
    - 停止フラグ検出、例外捕捉（loop 内でのログ出力）を実装。
- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーに stdout StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。
    - ログディレクトリの自動作成、既存ハンドラのクリア、LOG_LEVEL/LOG_DIR の解決ルールを実装。
    - ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続するフォールバックを実装。
- プロセス優先度・CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
    - CPU affinity 固定機能 `set_cpu_affinity` を追加。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` パッケージを追加。純粋関数群で構成（DB 非依存、メモリ内計算）。
  - portfolio_builder:
    - `select_candidates`（スコア降順・同点タイブレーク）を追加。
    - `calc_equal_weights`（等金額配分）を追加。
    - `calc_score_weights`（スコア加重配分、全スコアが 0 の場合は等配分へフォールバック）を追加。
  - risk_adjustment:
    - `apply_sector_cap`（セクター集中制限により候補をフィルタ）を追加。
    - `calc_regime_multiplier`（市場レジームに応じた投下資金乗数、未知レジームは 1.0 でフォールバック）を追加。
  - position_sizing:
    - `calc_position_sizes`（allocation_method に応じた株数決定、risk_based / equal / score 対応）を追加。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash を超える場合のスケールダウン）、コストバッファ反映、残差を考慮した追加配分ロジックを実装。
  - パッケージ __init__ で上記関数を公開。
- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標を集計し、Pass/Fail を判定するレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 など。
    - P95 計算、日付フィルタ（--from / --to）、閾値による PASS/FAIL 判定を実装。
- 研究（リサーチ）モジュール開始
  - `kabusys.research.factor_research` を追加（モメンタム等のファクター計算方針を実装開始）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計。
    - モメンタム関連定数・設計方針を定義（calc_momentum の実装開始）。

### Changed
- なし（初回リリースのため新規追加が中心）

### Fixed / Robustness
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に警告を出し処理を継続するように改善（テスト実行環境等での安全性向上）。
- ロギング初期化の安全化
  - ログディレクトリ作成やファイルハンドラ生成に失敗しても stdout にフォールバックして動作を継続するように実装。
- プロセス優先度/affinity の失敗耐性
  - 権限不足や未サポート環境で例外を抑制し、警告を出してスキップする実装により起動安定性を向上。

### Notes / Implementation Details
- run_execution は paper_trading 環境で本番 DB と分離するため `paper_sqlite_path` を使用します。監視側（run_monitoring）は環境に関係なく `sqlite_path`（本番監視 DB）を使用する設計です。
- `MONITOR_POLL_INTERVAL`（秒）で監視ポーリング間隔を上書き可能。0 以下や不正値はデフォルト（60 秒）にフォールバックして警告を出します。
- `validate_config` は PyYAML 非依存で、PyYAML が無い場合は YAML 検証をスキップして警告を表示します。
- position_sizing の aggregate スケーリングは小数切り捨て・単元株丸め・残差配分ロジックを含み、利用可能現金に基づくスケーリングを行います。

---

今後の予定（想定）
- research モジュールのファクター計算関数を完成させる（calc_momentum の続きなど）。
- ExecutionEngine / SystemMonitor 周りの E2E テスト追加。
- strategy / execution 設計に沿った config ファイル自動生成スクリプト等の拡充。