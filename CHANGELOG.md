# CHANGELOG

すべての notable な変更点を Keep a Changelog 準拠で日本語にて記載します。

フォーマット:
- 変更はセクションごとに分類（Added, Changed, Fixed, Removed 等）
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせて 0.1.0 とし、リリース日を 2026-04-18 としています（推定）。

## [Unreleased]
- （現時点のコードベースは初版リリース相当の内容のため、未リリース差分はありません）

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期リリース。KabuSys 自動売買システムの基礎モジュール群を追加。
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数から各種設定を読み出す統一インターフェースを提供。
    - J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / プロセス関連設定等のプロパティを実装。
    - `env` プロパティで `development` / `paper_trading` / `live` を検証。
    - `paper_fill_mode` の有効値検証（"instant" | "partial" | "never" | "reject"）。
    - paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を分離して扱う仕組みを提供。
  - .env 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み順: OS 環境 > .env > .env.local（.env.local は上書き可）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` ファイルパーサはクォート / エスケープ / コメントを考慮して頑健にパース。

- 設定支援 CLI
  - config_setup（src/kabusys/config_setup.py）を追加。
    - 対話式ウィザードで .env を生成・更新可能。
    - 必須項目やデフォルト、選択肢、シークレット項目をサポート。生成される .env にコミットしない旨のヘッダを含む。
  - 設定検証ツール validate_config（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 任意）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 監視 / 実行起動スクリプト
  - run_monitoring（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor のポーリングループを起動。停止はプロジェクト内 `data/stop_requested.flag` を検知して行う。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックし警告を出力。
    - 監視コンポーネントは環境にかかわらず production の sqlite_path を使用する設計（監視データは本番と一元化）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution（src/kabusys/run_execution.py）を追加。
    - ExecutionEngine を起動するスクリプト。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。停止は `data/stop_requested.flag`、PID 管理は `data/execution.pid` を使用。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全停止するループを実装。

- ロギング & プロセス管理ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をセットアップするユーティリティ。
    - ログ出力先ディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使用する点を明示（cron / Task Scheduler のリダイレクト運用に配慮）。
  - process_priority（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - psutil を使用。CPU affinity を設定する set_cpu_affinity 関数も提供。
    - 権限不足などで設定できない場合は警告ログでスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights: 等金額配分（各重み = 1/N）。
    - calc_score_weights: スコア加重（スコア合計が 0 の場合は等金額にフォールバックし WARNING）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別時価を基にセクター集中を防ぐ候補除外ロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 でフォールバックし警告を出す。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装。
      - risk_based: risk_pct, stop_loss_pct を元にポジションサイズ算出。
      - equal / score: ウェイトに応じて割付。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下金額上限（max_utilization）を実装。
      - aggregate cap により全体コストが available_cash を超える場合はスケーリングし、残余キャッシュで端数分（lot 単位）を再配分するアルゴリズムを実装。
      - cost_buffer を考慮して手数料・スリッページを保守的に見積もる。

- 研究用ファクター計算
  - research/factor_research（src/kabusys/research/factor_research.py）
    - DuckDB 接続を受け、prices_daily / raw_financials を元に Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計の基盤を追加。
    - モメンタム計算のための定数や calc_momentum の骨組み（引数・返り値仕様）を追加。営業日ベースのホライズン、MA200 の扱いなどを注記。

- ツール
  - tools/paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等を集計。
    - デフォルト DB は data/paper_trading.db。コマンドライン引数で期間（--from/--to）および --db を指定可能。
    - 基準値（閾値）を定義し PASS/FAIL を判定: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms。

### Changed
- （初版のため「変更」は特に無し。将来のリリースで差分を記録）

### Fixed
- （初版のため「修正」は特に無し）

### Removed
- （初版のため「削除」は特に無し）

### Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトへフォールバックし、ログ出力する設計。
- run_execution は paper_trading モード時に paper 用 DB を使うため、本番 DB とデータが混ざらないことを意図している。
- logging_setup はログディレクトリ作成に失敗した場合にフォールバックし、運用環境においてもログ出力の途切れを防止する配慮がある。
- config の .env パースはクォート中のエスケープやインラインコメント処理を考慮し、より現実的な .env フォーマットに対応している。
- process_priority はプラットフォーム依存の差を吸収するが、権限不足などで設定できない場合も graceful にスキップする。

---

（この CHANGELOG は与えられたコードベースの内容から推測して作成したものです。実際のコミット履歴やリリースノートがある場合は、それに合わせて修正してください。）