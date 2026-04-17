# Changelog

すべての非互換性のある変更はメジャーリリースとして記載します。本ファイルは Keep a Changelog の形式に従います。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。

- 環境設定・ロード
  - `.env` 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - `.env` パーサーを強化:
    - export プレフィックス対応（`export KEY=value`）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし行のインラインコメント取り扱い（直前が空白またはタブの `#` をコメントとして解釈）。
  - `_load_env_file` にて OS 環境変数を保護する protected オプションを導入（既存の OS 環境変数を上書きしない）。
  - `Settings` クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に:
    - J-Quants / kabu API / LINE / DB（DuckDB/SQLite）/各種監視閾値/環境種別など。
    - `PAPER_FILL_MODE` の妥当性検証（`instant`/`partial`/`never`/`reject`）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の入力検証と利便性メソッド（`is_live`/`is_paper`/`is_dev`）。

- 設定ウィザード CLI
  - `kabusys.config_setup` を追加（対話式ウィザードで `.env` を作成・更新）。
  - 主要設定項目の定義と読み書きロジックを提供（秘匿項目マスク表示、既存値読み込み、選択肢サポート等）。
  - `.env` のテンプレート出力および保存指示を実装。

- 設定検証 CLI
  - `kabusys.validate_config` を追加（起動前に .env と config/*.yaml の状態を検証）。
  - 必須/任意環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がある場合）を実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - `run_execution.py`:
    - 起動時にプロセス優先度を「high」に設定する仕組みを導入。
    - `KABUSYS_ENV=paper_trading` 時は paper 用の SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用して本番 DB と分離。
    - ブローカークライアント作成のための `BrokerClientFactory` を利用。paper_trading 時は MockBrokerClient を利用する想定。
    - 注文リポジトリ、OrderManager、RiskManager、Reconciler を組み立て `ExecutionEngine` をスレッドで実行。停止フラグ（data/stop_requested.flag）検知による安全停止をサポート。
    - `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等）。
    - 実行用 PID ファイルの取り扱い（`data/execution.pid`）をサポート。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正入力はデフォルトにフォールバックし警告を出す）。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する設計（監視データは本番 DB に保存）。
    - 停止フラグ検知でループを終了。例外はログに記録して次ポーリングに備える。

- 監視関連
  - `monitoring_db.init_monitoring_db` の呼び出しにより監視用テーブルを確保（両ランナーで利用）。

- ポートフォリオ構築ライブラリ（純粋関数）
  - `portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等分にフォールバックして警告）。
  - `portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター比率が閾値超過のセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（`bull`/`neutral`/`bear` のマッピング、未知レジームは警告のうえフォールバック）。
    - 実装上の注意点（price 欠損時の挙動に関する TODO コメントあり）。
  - `portfolio.position_sizing`:
    - 発注株数算出 `calc_position_sizes`（`risk_based` / `equal` / `score` をサポート）。
    - 単元株（lot）丸め、1銘柄上限、aggregate キャップ（available_cash）に基づくスケーリングロジックを実装。
    - コストバッファ（手数料・スリッページ見積り）を反映し、残余キャッシュで端数を lot_size 単位で再配分するアルゴリズムを搭載。
    - 将来的な拡張（銘柄ごとの lot_map）は TODO コメントで明示。

- 研究モジュール（DuckDB を使用）
  - `research.factor_research`:
    - モメンタム `calc_momentum`（1M/3M/6M リターン、MA200 乖離率）を DuckDB SQL で計算。
    - ボラティリティ/流動性 `calc_volatility`（ATR20、相対 ATR、20日平均売買代金、出来高比率）を算出するクエリを実装。
    - DuckDB 接続を受け取り、prices_daily テーブルから計算する設計。

- ツール
  - `tools.paper_verification_report`:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力（閾値はソース内定数で定義）。
    - 日付フィルタ、DB パス引数・環境変数サポート、P95 算出ユーティリティを実装。

- ユーティリティ
  - `utils.process_priority`:
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定 `set_process_priority` を実装（psutil 利用）。
    - CPU affinity 固定 `set_cpu_affinity` を追加（指定コア数で先頭 N コアにピン留め、例外時は警告でスキップ）。
    - 権限不足や未対応環境での安全なフォールバック処理とログ警告を実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Notes / Known issues
- 一部の箇所に将来的な拡張・改善を示す TODO コメントあり（例: position_sizing の銘柄別 lot サイズ、risk_adjustment の price 欠損対処）。
- `research.factor_research` や `validate_config` の YAML パースは PyYAML が存在しない場合はスキップ／警告となる。
- プロセス優先度・CPU affinity の設定は OS 権限や psutil の実装状況に依存し、設定失敗時は警告でスキップされる。

---

出典: リポジトリ内のソースコードを元に機能・設計を推測して作成。開発中の変更や追加は随時この CHANGELOG に追記してください。