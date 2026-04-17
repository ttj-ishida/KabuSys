# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（以下は提供されたコードベースから内容を推測してまとめたリリースノートです。）

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。KabuSys の核となる機能群と開発用ツールを導入。

### Added
- 基本ライブラリ・バージョン情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - Settings クラスを導入。環境変数経由で各種設定を取得可能（J-Quants / kabuステーション / LINE / DB / 監視閾値等）。
  - 自動的にプロジェクトルートの `.env` と `.env.local` を読み込む仕組みを追加（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - `.env` パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープをサポート）。
  - 各種プロパティで入力値の検証を実施（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等）。
  - デフォルトパス/値の設定（DuckDB/SQLite/デフォルト API URL 等）。

- 環境設定ウィザード
  - `kabusys.config_setup`：対話式で `.env` を作成・更新する CLI を追加。
  - 主要項目（環境、API トークン、DB パス、ログレベル、Kill Switch 設定など）をウィザードで入力・保存可能。

- 設定検証ツール
  - `kabusys.validate_config`：.env と config/*.yaml の存在・妥当性をチェックする CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パス親ディレクトリチェック、YAML のパース検証（PyYAML が利用可能な場合）を実装。
  - `--strict` オプションで警告も失敗扱いにできる。

- 実行ランチャー / 監視ランチャー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時はペーパートレード用 DB を使用し本番 DB と分離。
    - Broker クライアントをファクトリ経由で生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行。
    - 停止用フラグファイル（data/stop_requested.flag）を監視して安全に停止。
    - 実行中 PID ファイルの記録（data/execution.pid など）。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 停止フラグファイルを検知してループ終了。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`：プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）に対応した実装。
    - アクセス権限や未サポート環境では警告を出して安全にフォールバック。

- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio.portfolio_builder`：
    - 候補選定 select_candidates（スコア降順、タイブレークルールあり）。
    - 等分配 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等分配にフォールバック）。
  - `portfolio.risk_adjustment`：
    - apply_sector_cap：セクター集中制限ロジック。既存保有と売却予定を考慮して候補をフィルタ。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - `portfolio.position_sizing`：
    - calc_position_sizes：等配分/スコア配分/リスクベースの株数計算、単元株（lot）丸め、aggregate cap によるスケーリング、コストバッファ対応。

- リサーチ / ファクター計算
  - `research.factor_research`：
    - DuckDB 接続を用いて Momentum（1M/3M/6M, MA200乖離）や Volatility（ATR、20日平均売買代金、出来高比など）を計算する関数を実装。
    - 計算に必要なスキャン期間や欠損データへの扱いを明確化。

- ペーパートレード検証ツール
  - `tools.paper_verification_report`：ペーパートレード用 SQLite DB から検証レポート（稼働率、注文成功率、送信率、レイテンシなど）を生成するスクリプトを追加。
    - デフォルト DB パス `data/paper_trading.db`。環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで指定可能。
    - P95 レイテンシや各種閾値（稼働率 99%、成功率 90% など）による PASS/FAIL 判定を出力。

### Changed
- （初回リリースにつき当該なし）

### Fixed
- （初回リリースにつき当該なし）

### Security
- 機密情報（API トークン、パスワード等）は .env に記載する設計。config_setup に .env を生成する旨の注意を明記（.env を Git にコミットしないことを推奨）。

### Notes / Usage
- 主要 CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証:   python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動:   python -m kabusys.run_monitoring
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]
- デフォルトの DB / ファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db
  - PID / フラグ: data/execution.pid, data/stop_requested.flag 等
- 本リリースはコードベースから推測してまとめたものであり、実際の運用手順や追加ドキュメントは併せて参照してください。

---

（翻訳・要約: 提供されたソースコードの内容から機能・仕様を抽出して CHANGELOG 形式でまとめました。）