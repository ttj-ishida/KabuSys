# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このリポジトリはセマンティックバージョニングを採用しています。

なお、本 CHANGELOG はソースコードの内容から推測して作成した要約です（実装コメント・TODO からの推測を含みます）。

## [Unreleased]

(なし)

---

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。本バージョンで導入された主要機能を列挙。
- 実行エントリポイント／運用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御はプロジェクトの data/stop_requested.flag によるフラグ検知。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合に Paper Trading 用（MockBrokerClient）を使用し、data/paper_trading.db（または環境変数で指定）に記録して本番 DB と完全分離。
    - 実行中は PID ファイル (data/execution.pid) 管理および停止フラグ監視を行う。
- 設定関連
  - `kabusys.config` モジュール
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロード（`.env` と `.env.local`、ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
    - .env ファイルパーサは `export` プレフィックス、クォート（シングル／ダブル、エスケープ対応）、インラインコメント処理等に対応。
    - `Settings` クラスで各設定値をプロパティとして提供（ENV 検証、デフォルト、型変換を含む）。
    - `PAPER_FILL_MODE` 等の厳格な検証を実装。
  - config_setup.py
    - 対話式ウィザードで `.env` の初期作成・更新を支援。シークレットはマスク表示。生成テンプレートを出力。
  - validate_config.py
    - 起動前検証 CLI を提供。必須環境変数やパス、config/*.yaml の存在や YAML パース（PyYAML がある場合）をチェック。`--strict` で警告を FAIL 扱いにするオプションを追加。
    - 本番環境向けのガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START 設定の危険性等）を実装。
- DB 初期化・接続
  - 監視用テーブル保証のため `init_monitoring_db` を実行する仕組みを導入（冪等に動作）。
  - SQLite（監視／paper_trading 用）と DuckDB（分析用）の接続を運用スクリプトから確立。
- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler を設定。
    - `LOG_LEVEL` / `LOG_DIR` / 引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`
    - psutil を用いて Windows/Linux/macOS でプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を設定する `set_cpu_affinity` を実装（利用不可時は警告を出してスキップ）。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、タイブレークロジック）、
    - 等金額／スコア加重配分 `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限適用 `apply_sector_cap`（既存保有のセクター別エクスポージャ算出、上限超過セクターの候補除外）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear をサポート、未知のレジームは警告後フォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 株数決定ロジック `calc_position_sizes`（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ考慮）を実装。
    - スケールダウン時の残差配分アルゴリズム（fractional remainder に基づく lot 単位での追加配分）を実装。
- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の DB を解析して検証レポートを出力する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。閾値に基づく Pass/Fail 判定を実装。
    - `--from` / `--to` / `--db` オプションをサポート。
- 研究モジュール（ファクター計算）
  - `kabusys.research.factor_research` の骨組み（モメンタム等のファクター計算の実装基盤）を追加。DuckDB を用いた計算を想定（prices_daily / raw_financials 参照）。一部実装（calc_momentum の導入）あり。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数の妥当性チェックとフォールバックを強化
  - `MONITOR_POLL_INTERVAL` が不正値（0 以下や非整数）の場合はデフォルトにフォールバックして警告出力。
  - `PAPER_FILL_MODE` の許容値チェックを実装し、不正値で ValueError を送出。
  - `KABUSYS_ENV` / `LOG_LEVEL` の不正値は明確な例外または警告で通知。

### Security
- .env の生成ウィザードと README 内テンプレートにて、.env を絶対に Git にコミットしないよう明示。
- validate_config の live ガードにより、本番環境での重要設定不足（LINE 通知等）が警告される仕組みを追加。

### Notes / Known limitations / TODO
- apply_sector_cap 内の価格欠損（price = 0.0）に関する注記あり：将来的に前日終値や取得原価を用いるフォールバックの検討が必要。
- position_sizing:
  - 将来的に銘柄別の lot_size をサポートするための拡張（stocks マスタ／lot_map）が想定されている（TODO コメントあり）。
  - price の欠損時にエラーではなくスキップする挙動のまま。
- research.factor_research はモジュール骨格と一部関数の実装があるが、完全実装ではない可能性あり（ファイル末端が途中で切れている/実装継続を示唆するコメントあり）。
- ログディレクトリ作成失敗時はファイルログを無効化して stdout のみで継続する設計のため、該当環境ではログ永続化が行われない点に注意。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム差分で設定に失敗する可能性があり、その場合は警告を出力してスキップする。

---

著者注:
- この changelog はソースコード内のコメント、関数名、ドキュメント文字列、TODO コメント等から機能と設計意図を要約したものです。実際のリリースノート作成時にはコミット履歴・ PR 説明と合わせて正確な差分を反映してください。