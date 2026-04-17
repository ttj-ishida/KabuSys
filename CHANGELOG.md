# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日（本コードベースから推測）です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 起動スクリプト / 実行制御
  - run_execution.py を追加。ExecutionEngine の起動用 CLI ラッパーを提供。
    - プロセス優先度を高に設定して起動（utils.process_priority.set_process_priority を利用）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出による安全なシャットダウン処理を実装。
    - ExecutionEngine を別スレッドで実行し、停止検出時に engine.stop() を呼ぶループを提供。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視では環境にかかわらず本番の sqlite_path を使用する設計になっている点を明記。
    - 停止フラグ検出、例外時のログ出力、正常なクローズ処理を実装。

- 設定・環境読み込み
  - config.py を追加。
    - プロジェクトルート（.git または pyproject.toml）を自動検出し .env / .env.local の自動読み込みを行う（無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供）。
    - .env の行パーサを強化（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
    - 環境変数取得用 Settings クラスを提供（J-Quants / kabuAPI / DB / 監視閾値 / 各種フラグなど多数のプロパティ）。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode` 等をサポート。
  - config_setup.py を追加。対話式ウィザードで .env を初期作成・更新するツールを提供。
    - 複数設定項目のプロンプト、既存値の読み込み、シークレット項目のマスク、保存確認まで実装。

- 設定検証ツール
  - validate_config.py を追加。起動前に .env や config/*.yaml の妥当性をチェックする CLI。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML が利用可能な場合）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築・サイズ計算
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）：スコア降順、同点は signal_rank によるタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（既存保有のセクター別エクスポージャー算出、上限超過セクターの新規候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知の値はフォールバック＆警告）。
  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）：allocation_method に応じた計算（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）に基づくスケーリング、残余を fractional remainder に基づいて割り当てるアルゴリズムを実装。
    - price 欠損時のスキップ、コストバッファ（cost_buffer）による保守的見積りをサポート。

- 研究用ファクター計算
  - research/factor_research.py を追加（DuckDB を用いた定量ファクター計算）。
    - モメンタム計算（calc_momentum）：1M/3M/6M リターン、MA200 乖離率（データ不足時は None を返す）。
    - ボラティリティ/流動性計算（calc_volatility）を実装（ATR, avg_turnover, volume_ratio 等）。
    - DuckDB 接続を受け、SQL＋Python で計算する設計。

- ユーティリティ
  - utils/process_priority.py を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（set_process_priority）。
    - CPU affinity 固定ユーティリティ set_cpu_affinity（利用不可/権限不足時は警告ログでスキップ）。

- 運用ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用の検証レポート生成ツール。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定。
    - デフォルト DB パスは `data/paper_trading.db`。`--from`/`--to`/`--db` オプションをサポート。
    - P95 計算の実装および閾値（稼働率 >=99%、fill_rate >=90% 等）を定義。

- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。

### Changed
- デフォルト動作・安全性
  - .env 自動ロードは OS 環境変数を優先し、.env.local が .env を上書きする仕組みを採用（既存環境を保護するため protected キーを利用して上書きを制御）。
  - 監視（run_monitoring）は本番 sqlite を使う決定がコード内で明示されている（環境に依存しない監視 DB の取り扱い）。

### Fixed
- .env パーシングの堅牢化
  - 引用符・エスケープ・インラインコメントの扱いに関する様々なケースに対応し、誤ったパースを防止。

### Security
- .env の注意喚起
  - config_setup に .env を絶対に Git にコミットしない旨のヘッダコメントを追加。

### Deprecated
- なし

### Removed
- なし

---

注:
- 上記はリポジトリ内のソースコードと docstring から推測してまとめた CHANGELOG です。実際のリリースノート作成時は、変更の粒度や日付、関係者情報などを併せて調整してください。