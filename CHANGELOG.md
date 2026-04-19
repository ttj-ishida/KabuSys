# Keep a Changelog

すべての変更は semver に従って記載します。  
このファイルはプロジェクトの主な追加機能、変更点、既知の制約をコードベースから推測してまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 実行系エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離する仕組みを導入。
    - BrokerClientFactory によるブローカークライアント生成を導入（本番/モックの切替を想定）。
    - OrderRepository、OrderManager、RiskManager（デフォルト RiskConfig の設定を含む）、Reconciler を組み立てて ExecutionEngine を起動。
    - 起動前/実行中に `data/stop_requested.flag` を監視し、停止要求を検知すると安全にエンジンを停止する制御を実装。
    - 実行時に PID を `data/execution.pid` に書き込む仕組みを前提（設定経由で指定可能）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動する CLI スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下や非整数）の場合は警告を出してデフォルトにフォールバック。
    - 監視は環境に依らず本番の sqlite_path を使用する実装（監視データを一元管理する設計）。
    - 停止フラグファイルを監視して安全にループを抜ける挙動を実装。

- 設定管理
  - config.py
    - .env 自動読み込み機能を提供（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - .env の読み込み順と保護（OS 環境変数を上書きしない挙動）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロード無効化が可能。
    - .env の各行パーサは `export KEY=val`、引用符（シングル/ダブル）およびバックスラッシュエスケープ、インラインコメントの処理に対応。
    - Settings クラスを導入し、環境変数アクセスをプロパティ化。主要設定:
      - J-Quants / kabuステーション / LINE / DB パス（DuckDB / SQLite / paper_trading SQLite）
      - PID / kill flag パス、kill_flag_clear_on_start フラグ
      - CPU/MEM/DISK しきい値
      - KABUSYS_ENV 検証（development/paper_trading/live）
      - LOG_LEVEL 検証
      - paper_fill_mode の検証（"instant"|"partial"|"never"|"reject"）
    - settings = Settings() を提供。

- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 各設定項目の説明、デフォルト、シークレット扱い、選択肢チェックを提供。
    - 既存 .env の読み込み、Enter による既存値の再利用、最終確認後に .env を書き込む機能を実装。
  - validate_config.py
    - 起動前に .env および config/*.yaml の基本的な検証を実行する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パーサ（PyYAML 利用可否に応じたパース検証）を実装。
    - `--strict` オプションで警告も FAIL として扱う。

- ロギングユーティリティ
  - utils/logging_setup.py
    - 共通のログ初期化関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップするフォールバックを実装。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - カレントプロセスの優先度設定 `set_process_priority(level)` を追加（Windows/Linux/macOS を吸収）。
    - CPU アフィニティを設定する `set_cpu_affinity(cpu_count)` を追加。
    - psutil が提供する OS 固有定数の扱い、権限不足時の警告フォールバックを実装。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補銘柄選定 `select_candidates(buy_signals, max_positions)` を追加（スコア降順、タイブレークに signal_rank を利用）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を追加（全スコアが 0 の場合は等配分にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を追加。既存保有のセクター別時価から上限超過セクターの候補を除外する。
    - マーケットレジームに応じた資金乗数 `calc_regime_multiplier(regime)` を追加（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 `calc_position_sizes` を追加。下記特徴を持つ:
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: 損切り幅・リスク許容率から発注株数を算出。
      - equal/score: weight に基づいて各銘柄の目標株数を計算。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮し、必要に応じてスケールダウンして残差を lot 単位で再配分するアルゴリズムを実装。
      - cost_buffer（スリッページ・手数料見積り）を考慮。

- モニタリング / DB 初期化
  - monitoring.monitoring_db: 監視用テーブルの初期化を行う init_monitoring_db を用意（run_monitoring と run_execution から呼び出し、冪等的に監視テーブルを保証）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）から期間指定で検証レポートを生成する CLI を追加。
    - 指標:
      - 稼働率（uptime_pct）・総ポーリング数・エラー数
      - 注文成功率（fill_rate）、送信率（send_rate）、Created/Filled/Sent 件数
      - リスク却下数（risk_logs）
      - レイテンシ（avg / max / P95）。P95 の計算ロジックを実装
    - Pass/Fail 判定基準を定義（例: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - DB が存在しない場合のエラーメッセージ出力、期間フィルタの引数（--from/--to）対応。

- リサーチ・ファクター計算基盤
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加。設計として:
      - Momentum / Value / Volatility / Liquidity の計算を想定。
      - calc_momentum(conn, target_date) 等の関数により prices_daily / raw_financials テーブルを参照して (date, code) ベースの結果を返す方針。
    - （注）ファイル末尾に続きがあることを示唆する実装で、用途設計と定数が含まれている。

- パッケージ構成
  - package の __all__ / エクスポートが設定され、 portfolio モジュールで主要関数をまとめてエクスポート。

### Changed
- （初期リリースのため変更履歴はありません）

### Fixed
- （初期リリースのため修正履歴はありません）

### Known limitations / Notes（既知の制約・設計メモ）
- factor_research.py は設計・定数が含まれているが、実装が途中の箇所（ファイル末尾に断片的な記述）があるように見受けられます。完全実装が必要です。
- apply_sector_cap のエクスポージャー計算は price が欠損（0.0）の場合に過少見積りのリスクがある旨の TODO コメントあり。将来的にフォールバック価格（前日終値など）を導入することが示唆されています。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム差によって実行できない場合があり、その場合は警告を出してスキップするフォールバックが組み込まれています。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後や特殊な配置では自動ロードがスキップされる場合があります。必要に応じて環境変数で明示的に設定してください。
- ログディレクトリ作成やファイルハンドラの作成に失敗した場合、ログは stdout のみで出力されます（意図的なフォールバック）。
- Paper Trading と本番の DB 分離は設計として実装済みだが、運用ルール（どの環境でどの DB を使うか）は .env の設定に依存します。

---

今後の推奨:
- factor_research の完全実装とユニットテストの追加。
- 主要ロジック（position sizing、risk manager 等）に対する包括的な単体テストおよびシミュレーション検証。
- ドキュメント（PortfolioConstruction.md, StrategyModel.md など参照されている設計文書）が存在することを前提に、該当ドキュメントをリポジトリに同梱するとユーザー理解が向上します。

以上。必要であれば CHANGELOG の英文版や、各変更点ごとの関連ファイル/関数の一覧も作成できます。