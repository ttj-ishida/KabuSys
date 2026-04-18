# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」方式に準拠しています。

なお、本リポジトリはバージョン 0.1.0 の初期公開相当の状態と推測されるため、以下はソースコードから推測して作成した初回リリースの変更履歴です。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初期リリース。アプリケーションのコア機能群（設定管理、起動スクリプト、ログ設定、プロセス制御、ポートフォリオ構築等）を追加。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - .env の読み込み順序: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 強化された .env パーサーを実装（`export KEY=val` 対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント扱いの改善）。
  - `Settings` クラスを導入して環境変数をプロパティ経由で取得。各種検証（KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、PAPER_FILL_MODE の有効値チェック等）を組み込み。
  - デフォルトパスとキー:
    - DuckDB: `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）
    - SQLite(監視用): `SQLITE_PATH`（デフォルト: `data/monitoring.db`）
    - ペーパー取引用 SQLite: `PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）
    - 各種しきい値・ファイルパスのプロパティ化（PID / Kill flag / resource thresholds 等）。

- 環境セットアップ / 検証 CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成・更新する CLI を追加（必須/任意項目の入力、シークレット表示マスク、保存確認など）。
  - `kabusys.validate_config`：環境変数および `config/*.yaml` の存在・簡易検証を行う CLI を追加。`--strict` を指定すると警告も失敗扱いにできる。
  - `validate_config` は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出す。

- 起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。
    - Broker クライアントのファクトリを利用して実運用/モックを切替可能。
    - プロセス優先度を高く設定し、PID ファイル管理および停止フラグ検出をサポート。
  - `run_monitoring.py`：SystemMonitor（監視）起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視用 DB 接続と duckdb 接続を確立、監視ループで `SystemMonitor.check_once()` を繰り返す。停止フラグを検知して安全に終了。

- ログ / プロセスユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーを統一的に設定（コンソール stdout と日次ローテートファイル出力を追加）。
    - ログディレクトリが作れない場合はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定。CPU affinity を設定するユーティリティも提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（score 降順、タイブレークとして signal_rank）: `select_candidates`
    - 重み計算: 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合に等配分へフォールバックして warning を出力）
  - `kabusys.portfolio.risk_adjustment`
    - 同一セクターの集中を抑える `apply_sector_cap`（当日売却予定銘柄を除外するロジックをサポート、"unknown" セクターは制限対象外）
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear をマップ。未知のレジームは 1.0 でフォールバック）
  - `kabusys.portfolio.position_sizing`
    - ポジションサイズ算出 `calc_position_sizes`
      - allocation_method: "risk_based" / "equal" / "score" に対応
      - 単元株（lot_size）、手数料/スリッページ見積り（cost_buffer）を考慮した aggregate cap 調整ロジック
      - available_cash に対してスケーリングし、端数は lot_size 単位で残差最大順に再配分
      - 現状は全銘柄共通の lot_size を想定（将来的な拡張をコメントで明示）

- 解析 / ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ等を集計し、PASS/FAIL 判定を行う。
    - コマンドライン引数で期間指定（--from, --to）や DB パス指定（--db）をサポート。
    - P95 計算や各種閾値（稼働率 99%, 成功率 90% 等）を内蔵。
  - `kabusys.research.factor_research`：
    - モメンタム・ボラティリティ・バリュー等のファクター計算モジュールを実装開始。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし（実装段階での安定化・堅牢化を反映）。

### Known issues / Notes
- research.factor_research モジュールはソース内で途中（ファイル末尾付近に未完のコードが存在）であり、完全実装は未完了の可能性がある。利用時は注意。
- `apply_sector_cap` 内で価格が 0.0 の場合にエクスポージャーが過少見積りされる旨の TODO コメントがあり、将来的にフォールバック価格（前日終値など）を導入することが推奨されている。
- `calc_position_sizes` は現状すべての銘柄で共通の lot_size を仮定している（将来的に銘柄別 lot_size をサポートする TODO）。
- process_priority / set_cpu_affinity は権限や OS に依存するため、権限不足時は警告を出して処理をスキップする設計になっている。
- logging_setup はログディレクトリの作成失敗時にファイル出力を自動で無効化するが、その場合はコンソールのみの出力となる。
- `.env` 自動ロードはプロジェクトルートの検出に依存する（.git / pyproject.toml が基準）。パッケージ配布後などで検出できない場合は自動ロードされない。

### Migration / Usage notes
- 新規導入時はまず `python -m kabusys.config_setup` を使って `.env` を生成し、その後 `python -m kabusys.validate_config` で設定検証することを推奨。
- 本番環境での Paper Trading と実本番 DB は分離される（`KABUSYS_ENV=paper_trading` で paper DB を利用）。
- 監視・実行プロセスはそれぞれ `run_monitoring.py` / `run_execution.py` を直接実行して起動できる。停止はプロジェクト内 `data/stop_requested.flag`（停止フラグ）や kill 関連フラグで制御。

### Breaking Changes
- 初回リリースのため該当なし。

---

この CHANGELOG はソースコードの実装状況から推測して作成しました。実際のリリースノートは開発者による確認の上で更新してください。