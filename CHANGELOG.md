# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: 本ログはソースコードを参照して推測に基づき作成したもので、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初回公開リリース。自動売買システムのコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築、検証ツールなどの基盤機能を実装。

### Added
- パッケージメタ情報
  - kabusys のバージョンを __version__ = "0.1.0" として設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するランナーを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用して実際のブローカー／モックを切り替え。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御をサポート。
    - Engine をバックグラウンドスレッドで実行し、停止フラグを監視して安全に停止するロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するランナーを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用する挙動を明記。
    - 停止フラグ検知でループを終了。

- 設定管理
  - config.py
    - .env ファイルの自動ロード（プロジェクトルート検出: .git または pyproject.toml）を実装。
    - .env のパースは引用符・バックスラッシュエスケープ・インラインコメントに対応。
    - OS 環境変数を保護するための上書きロジック（.env と .env.local の読み込み順と protected キー）を実装。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視閾値 / 環境判定などのプロパティを提供。
    - PAPER_FILL_MODE のバリデーション（"instant"/"partial"/"never"/"reject"）を実装。
    - 環境判定プロパティ（is_live, is_paper, is_dev）を提供。

- 設定ユーティリティ CLI
  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを実装。
    - デフォルト値、選択肢、シークレット入力のサポートと保存機能（.env への書き出し）。
    - 生成テンプレート（コメント付き）で .env を出力。

  - validate_config.py
    - 起動前設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス備考チェック、config/*.yaml の存在/パースチェック（PyYAML 任意で未インストール時はスキップ）等を実装。
    - --strict オプションで警告を失敗扱いにする機能を提供。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を実装。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定 set_process_priority を実装（Windows / POSIX 対応）。権限不足時は警告でスキップ。
    - CPU affinity 設定用の set_cpu_affinity を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート/上位選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター別時価を計算して候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各種配分方式（risk_based / equal / score）に基づく発注株数計算。
    - lot_size（単元）丸め、ポジション上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを実装。
    - risk_based 方式でのリスク計算（risk_pct, stop_loss_pct）に基づく株数算出をサポート。

- モニタリング関連
  - monitoring モジュールの初期化処理呼び出し（init_monitoring_db を run_execution/run_monitoring から起動時に呼び出して監視用テーブルを保証）。
  - stop flag / kill flag を利用した外部制御フローの実装（run_* スクリプトにて採用）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI を実装。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）、DB パスの CLI 引数 / 環境変数での指定をサポート。
    - P95 計算、欠損データに対する N/A の扱い、しきい値定義（99% uptime 等）を実装。

- 研究用ファクター計算（スケルトン）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを実装（Momentum / Value / Volatility / Liquidity の設計を記述）。
    - DuckDB 接続を受け取って prices_daily / raw_financials を参照する方針を採用。
    - 一部（calc_momentum の実装開始）を含むが、モジュールは拡張可能な設計になっている。

### Changed
- アプリケーション構成
  - run_* スクリプトと内部ユーティリティ群により、実行・監視・設定検証フローを明確に分離。
  - ロギング設定は全スクリプトで統一的に呼び出す構成に変更（setup_logging の利用を推奨）。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱いを改善。
  - .env のロードで OS 環境変数を保護するための protected キーサポートを追加。

### Known issues / Notes
- research/factor_research.calc_momentum はファイル末尾で途中となっており、完全実装が必要（ファクター計算はまだ拡張段階）。
- position_sizing の価格フォールバック
  - apply_sector_cap や calc_position_sizes が price_map/open_prices に 0.0 や欠損値があると過少/過大評価の可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックが望まれる。
- ログディレクトリ作成やプロセス優先度設定は環境（権限/OS）に依存し、失敗時は警告でスキップする設計。
- validate_config における YAML パースは PyYAML が未インストールだとスキップされるため、YAML 検証を確実に行いたい場合は PyYAML をインストールすること。

---

開発にあたっての補足:
- 設定ファイル（.env）や DB パス、KABUSYS_ENV の値に依存する処理が多いため、運用前に `python -m kabusys.validate_config` で設定を確認してください。
- .env は機密情報を含むため、git にコミットしないでください（config_setup の出力ヘッダにも注意喚起あり）。

---