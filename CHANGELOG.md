# Changelog

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の書式に準拠しています。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ構成を実装。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 環境設定/管理
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
    - 読み込み順: OS環境 > .env > .env.local（.env.local は上書き）。
    - OS側の環境変数を保護するための上書き制御を実装。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - 対話式設定ウィザード `kabusys.config_setup` を追加（`.env` の初期作成/更新を支援）。
  - 設定を表す `Settings` クラスを実装。各種環境変数へのアクセスラッパー（DB パス、API トークン、ログレベル、閾値など）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant"/"partial"/"never"/"reject"）。
    - `KABUSYS_ENV` の検証（"development" / "paper_trading" / "live"）。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。`.env` と `config/*.yaml` の存在・基本妥当性をチェック（`--strict` オプションで警告を失敗扱いにできる）。
  - PyYAML 未インストール時には YAML 検証をスキップし警告を出力する。
- ロギング
  - 汎用ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト: logs/<app_name>.log）をルートロガーに設定。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"`。
    - ログディレクトリ解決順: 引数 > 環境変数 `LOG_DIR` > デフォルト `logs/`。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
- プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority` を追加。Windows / POSIX を吸収してプロセス優先度（nice / Windows priority class）を設定する `set_process_priority` と、CPU コア固定の `set_cpu_affinity` を提供。
- 実行・監視スクリプト
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加。
    - 起動時にプロセス優先度を高 ("high") に設定。
    - `KABUSYS_ENV=paper_trading` の場合、専用のペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用して本番 DB と分離。MockBrokerClient を使う（BrokerClientFactory 経由）。
    - 停止制御: プロジェクトルート下の `data/stop_requested.flag` と `data/execution.pid` を使用して起動と停止を管理。
  - `run_monitoring.py`（SystemMonitor ポーリング起動スクリプト）を追加。
    - 環境に関わらず monitoring は本番の `sqlite_path` を使用して監視テーブルを初期化。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 停止フラグ検知でループを終了。
- DB / 分析
  - DuckDB と SQLite の接続を利用する設計を導入（`duckdb` / `sqlite3`）。
  - 監視テーブル初期化関数 `init_monitoring_db` を起動時に呼び監視テーブルの存在を保証（冪等）。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、タイブレーク: signal_rank）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクター比率を計算して上限超過セクターの新規候補を除外）。
    - レジームに基づく乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" -> 1.0/0.7/0.3、未知は 1.0 にフォールバックし警告）。
  - `kabusys.portfolio.position_sizing`:
    - 約定単位（lot）に合わせた株数算出 `calc_position_sizes`。
    - 配分方式: "risk_based"（リスクベース） / "equal" / "score" をサポート。
    - 1 銘柄上限、総投下キャッシュ上限、cost_buffer（手数料・スリッページ想定）を考慮したスケーリング、余剰キャッシュでの lot 単位追加配分アルゴリズムを実装。
    - 価格欠損時のスキップや上限計算を考慮。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ 等）を集計してレポート出力および PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ、閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を実装。
    - コマンドライン引数 `--from` / `--to` / `--db` を提供。

### 変更 (Changed)
- ログ出力の挙動を明確化:
  - stdout を StreamHandler に使用（cron 等からのリダイレクト運用を想定）。
  - 日次ローテーション・30 日保持のファイルハンドラを追加（logs/ に出力。作成失敗時はファイル出力を無効化）。
- 設定自動読み込みの保護:
  - OS 環境変数を破壊しないために .env 上書き時の protected set を導入。
- 実行コンポーネントの起動順序整理:
  - 起動時にプロセス優先度を最初に設定するよう標準化（run_execution / run_monitoring）。
  - 監視テーブルの初期化は起動時に必ず行うことで実行前の整合性を保証。

### 修正 (Fixed)
- 不正な `MONITOR_POLL_INTERVAL` 値（非整数や 0 以下）に対してデフォルトにフォールバックして例外を回避。
- .env パースのクォート/コメント処理を改善し、バックスラッシュエスケープに対応。
- `calc_score_weights` が全スコア 0 の場合に明確に等金額配分にフォールバックして警告を出すようにした。
- `process_priority` / `set_cpu_affinity` は権限不足や未実装 API に対して警告を出し処理を続行するよう堅牢化。

### ドキュメント (Documentation)
- 各 CLI スクリプトやユーティリティ関数に docstring と使用例を追加。
- config_setup による .env のテンプレート生成と注意書きを実装（.env を絶対に Git にコミットしない旨の注記）。

### 既知の制約 / 注意事項 (Known issues / Notes)
- validate_config は PyYAML がインストールされていない環境では config/*.yaml の内容検証をスキップし警告を出します（インストールを推奨）。
- monitoring は設計上「環境にかかわらず本番 sqlite_path を使用」します。ローカルで分離したい場合は環境変数 `SQLITE_PATH` を適切に設定してください。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別に拡張予定の旨コメントあり）。
- 一部のモジュール（研究系など）は引き続き拡張・テストが必要（実装の継続を想定）。

---

今後の変更に関してはこのフォーマットで逐次追記していきます。必要であれば、個別の機能/ファイルごとにより詳細なリリースノートを追記します。