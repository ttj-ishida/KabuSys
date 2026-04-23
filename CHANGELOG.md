# CHANGELOG

すべての変更は「Keep a Changelog」に準拠して日本語で記載しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- [0.1.0] - 2026-04-23: 初回公開リリース（コードベースから推測してまとめた実装内容）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動 / 実行関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内の `data/stop_requested.flag` によるフラグ検知で行う。
    - 起動時にプロセス優先度を "high" に設定し、SQLite（監視 DB）と DuckDB に接続して監視テーブルを初期化。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 DB を使用し MockBrokerClient を利用（本番 DB と分離）。
    - 停止用フラグ・PID 管理を実装（`data/stop_requested.flag`, `data/execution.pid`）。
    - バックグラウンドスレッドで ExecutionEngine を実行し、停止フラグで安全に停止する仕組みを提供。

- 設定関連
  - config.py
    - 環境変数読み込み・管理用 Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード（`.env` / `.env.local`、OS 環境変数を保護）。
    - `.env` のパースは export 形式・クォート・コメントなどに対応する堅牢な実装。
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading 設定、監視しきい値、環境種別検証など）を提供。
    - `paper_fill_mode`（"instant"|"partial"|"never"|"reject"）などのバリデーションを実装。
  - config_setup.py
    - 対話式設定ウィザードを実装して `.env` の初期作成・更新を支援。
    - デフォルト値、選択肢、シークレット入力の表示（マスク）をサポート。
    - `.env` の読み込み・書き込みロジックを提供（書き込む際のテンプレート付き）。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML がない場合は警告）等を行う。
    - `--strict` オプションで警告を失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 `setup_logging` を実装。
    - stdout 出力用 StreamHandler と日次ローテート（30日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows / POSIX）および CPU affinity 設定ユーティリティを実装。
    - psutil を使い、権限不足や未対応 OS の場合は警告ログを出してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates): score 降順、同点は signal_rank 昇順でタイブレーク。
    - 重み計算: 等分配 (calc_equal_weights)、スコア加重 (calc_score_weights)。全スコア 0 の場合は警告を出して等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限。既存保有のセクター別時価から上限超過セクターの新規候補除外（"unknown" セクターは除外対象から除く）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 でフォールバックして警告を出力。
  - portfolio/position_sizing.py
    - 各配分方式（risk_based, equal, score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（スリッページ・手数料）考慮、残差配分アルゴリズムを実装。

- リサーチ
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールの骨組みを実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - モメンタム指標（1M/3M/6M リターン、MA200 乖離等）計算関数の誘導を追加（実装途中）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを実装。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - CLI オプション `--from`, `--to`, `--db` をサポート。
    - デフォルト DB パスは `data/paper_trading.db`（環境変数で上書き可能）。

### 変更 (Changed)
- ログ設定とプロセス優先度の適用を各起動スクリプトの最初に行うよう統一（起動直後に set_process_priority と setup_logging を呼び出す）。
- 監視と実行で DuckDB / SQLite の利用方法を明確化（監視は常に本番 sqlite_path を使用、実行は paper_trading 環境で専用 DB を使用）。

### 修正 (Fixed)
- .env パーサ: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等の細部を実装して堅牢化。

### 注意事項 / 既知の制限 (Known issues)
- research/factor_research.py はモメンタム計算関数の途中でファイルが終端しており、完全実装は未完（骨組みは存在）。今後の実装で DuckDB クエリと全ファクターの計算を完成させる必要あり。
- process_priority の設定は psutil の権限制約や OS サポートに左右され、設定に失敗した場合は警告を出してスキップする実装になっている。
- position_sizing の lot_size は現在全銘柄共通で固定（将来的に銘柄別 lot_map への拡張予定がコメントとして存在）。
- .env 自動ロードはプロジェクトルートが特定できない場合スキップされる。テスト等の用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

---

その他、各モジュール内に詳細な docstring/コメントがあり、設計意図（PortfolioConstruction.md / StrategyModel.md 参照）や将来の拡張点が明記されています。今後のリリースでは research モジュールの完成、ExecutionEngine / Broker インターフェースの強化、テストカバレッジの追加などが想定されます。