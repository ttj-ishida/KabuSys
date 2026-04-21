# Changelog

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

現在バージョン
- [0.1.0] - 2026-04-21

## [0.1.0] - 2026-04-21
初回リリース。本リリースで追加された主要な機能・モジュールは以下の通りです。

### Added（追加）
- 基本情報
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。

- 設定管理・初期化
  - `kabusys.config`
    - .env 自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml`）。
    - `.env` と `.env.local` の読み込み順序、OS 環境変数の保護（上書き防止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 強力な行パーサー実装（コメント、`export ` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープの処理）。
    - `Settings` クラスにより環境変数をラップ。J-Quants / kabu API / DB パス / PAPER_TRADING 用設定 / 監視閾値 / 実行環境判定等をプロパティとして提供。
    - `paper_fill_mode` の入力検証（有効値チェック）。
  - `kabusys.config_setup`
    - 対話式ウィザードで `.env` を作成・更新する CLI を追加。シークレットのマスク表示、既存値の再利用、確認プロンプトを実装。
  - `kabusys.validate_config`
    - 起動前の設定検証用 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml の存在／パースチェック、live 環境向けガード（LINE 設定・KILL フラグ）を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行系・監視系スクリプト
  - `kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と完全分離。
    - Broker クライアントを生成（`BrokerClientFactory`）し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて別スレッドで実行。停止フラグ検知時に安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
  - `kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告ログ出力。
    - 監視データベースは環境に関係なく本番の `sqlite_path` を使用（監視テーブル初期化）。
    - 停止フラグ検出でループ終了、KeyboardInterrupt ハンドリング、接続クローズを保証。

- ポートフォリオ構築（純粋関数群）
  - `kabusys/portfolio/portfolio_builder.py`
    - シグナルのランク付け・候補選定: `select_candidates`
    - 等配分・スコア加重配分: `calc_equal_weights`, `calc_score_weights`（スコアが全て 0 の場合は等配分へフォールバックし WARNING 出力）
  - `kabusys/portfolio/risk_adjustment.py`
    - セクター集中リスク制御: `apply_sector_cap`（既存保有からセクター露出を算出し、上限超過セクターの新規候補除外）
    - レジームに応じた投下資金乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマッピング、未知レジームは警告とともに 1.0 でフォールバック）
  - `kabusys/portfolio/position_sizing.py`
    - ポジションサイズ算出: `calc_position_sizes`
      - 複数の配分方式に対応（risk_based / equal / score）。
      - 単元（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）に合わせたスケーリング、cost_buffer による保守的見積り、残差に基づく追加配分ロジック（再現性確保）を実装。
      - 価格欠損時のスキップやログ出力。

- ユーティリティ
  - `kabusys/utils/logging_setup.py`
    - 統一ログ設定ユーティリティ。コンソール出力は stdout を使用（cron/Task Scheduler のリダイレクトに配慮）、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を追加（30 日保持）。
    - 既存ハンドラをクリアしてから再設定することで二重設定を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys/utils/process_priority.py`
    - プロセス優先度設定（Windows / POSIX 差分吸収）。`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。権限不足等で失敗した場合は警告ログでスキップ。
  - `kabusys/utils/__init__.py`

- ツール
  - `kabusys/tools/paper_verification_report.py`
    - Paper Trading 向け検証レポート生成スクリプト（期間指定可能）。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し、閾値に基づく PASS/FAIL を出力。デフォルト DB は `data/paper_trading.db`（環境変数で変更可）。

- リサーチ
  - `kabusys/research/factor_research.py`
    - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity 等の設計・定数定義）。DuckDB 接続を受ける設計。モメンタム計算関数等の骨組みを実装（ファイル終端が一部省略されているが、prices_daily / raw_financials を参照する設計）。

### Changed（変更）
- ログ出力方針
  - stdout を標準出力に使うことで cron や Task Scheduler からのリダイレクト運用を想定。既存ハンドラは明示的に flush/close してから削除するように改善。

### Fixed（修正 / 安定化）
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ処理や、クォートなしでのインラインコメント検出条件を改善。export プレフィックスを許容。
- 環境関連の安全措置
  - .env 読み込み時に OS 環境変数を保護する仕組みを導入（.env/.env.local が OS 環境を不意に上書きしないように）。

### Notes（備考 / 今後の課題）
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合に保守的にスキップする実装だが、将来的には前日終値などのフォールバック価格を用いる検討がコメントとして残されている。
- research.factor_research.py は設計方針と一部実装（モメンタム計算の開始）を含み、ファイル末尾が途切れている（追加実装が必要）。
- Execution/Monitoring の多くのコンポーネント（BrokerClientFactory、ExecutionEngine、SystemMonitor など）は本リリースで起動・組立のロジックを含むが、内部の詳細実装（API 呼び出し等）は別モジュールに委譲されているため、テスト・本番運用時は各コンポーネントの実装状況に依存する。

---

以上が v0.1.0 の変更点です。追加・修正内容について不明点やドキュメント化（README/設計書への反映）や、リリースノートの詳細化が必要であれば指示ください。