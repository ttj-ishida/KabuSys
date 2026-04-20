# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、ソースコードから推測できる機能追加・改善・修正点を基に作成しています。

全部分は推測に基づく記述のため、実際のコミット履歴と一部差異がある可能性があります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

### Added
- プロジェクト初期リリース相当の主要機能群を追加。
- 実行エントリ／デーモン類
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパーの DB を分離し、BrokerClientFactory からブローカークライアントを生成してセッション実行を管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能。停止フラグファイルにより安全に終了。
- 設定・環境管理
  - config.py: 自動 .env ロード機能（.env, .env.local）の追加。.env の行パースを強化（export 形式対応、クォートとバックスラッシュエスケープ、インラインコメント処理）。Settings クラスを提供し、各種環境変数（J-Quants / kabu API / DB パス / Paper Trading 周り / 監視閾値 等）を型付きプロパティで取得可能に。
  - config_setup.py: 対話式ウィザードで .env ファイルを作成・更新する CLI を追加。
  - validate_config.py: 起動前設定検証用 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性検証、config/*.yaml の存在・パース検査（PyYAML が無ければスキップ）、--strict モードをサポート。
- 監視関連
  - monitoring 周りの初期化を行う init_monitoring_db 呼び出し（monitoring DB テーブルの冪等初期化）。
  - Settings に監視用閾値（CPU/MEM/DISK）や PID/KILL フラグパス等を定義。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 標準出力（stdout）への StreamHandler と 日次ローテーションされたファイル出力（TimedRotatingFileHandler）を設定するユーティリティを追加。ログディレクトリ作成に失敗した場合のフォールバックも実装。
  - utils/process_priority.py: psutil を用いたプラットフォーム横断のプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。Windows/Linux/macOS 等の差を吸収し、権限不足時は警告を出力してスキップ。
- Paper Trading / 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値に基づいた PASS/FAIL レポートを生成する CLI を追加。P95 計算、時間フィルタ（--from/--to）、DB パスのオーバーライドをサポート。既定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を採用。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、同スコアは signal_rank でタイブレーク）、等金額・スコア加重の重み計算（全スコアが 0 の場合は等重でフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有のセクター比率が閾値を超えるセクターを新規候補から除外）、市場レジームに応じた投下乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）。単元株（lot_size）での丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）考慮、残差の順序付けによる追加配分などを実装。
- research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム・MA200乖離・ATR 等の計算方針を実装、prices_daily/raw_financials 参照想定。ただしファイル末尾で一部未完の可能性あり）。
- パッケージ初期情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- DB 分離ポリシー明確化
  - run_monitoring は環境にかかわらず本番 sqlite_path（監視 DB）を使用する設計となっている旨を明示。
  - run_execution は KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離されるよう設計。
- .env 自動読み込みの挙動
  - OS 環境変数を保護するため読み込み時に既存の OS 環境変数を上書きしない（.env.local は override=True だが protected で保護）。
- ログ出力の標準化
  - 全起動スクリプトは setup_logging(app_name=...) を呼び出すことで、ログ出力のフォーマット・出力先を統一。
  - stdout を使う方針（stderr ではなく stdout）を採用し、タスクスケジューラや cron でのリダイレクト運用に配慮。
- 安全停止制御
  - 実行スクリプトはプロジェクトの data/stop_requested.flag による外部停止制御を採用。run_execution は起動中にフラグ検知で engine.stop() を呼び出す。

### Fixed
- 環境変数パースの堅牢化
  - export 前置、クォートされた値内のバックスラッシュエスケープ、インラインコメント判定（クォート無しで # の直前が空白の場合はコメントとみなす）などの処理を追加・修正し、.env の許容範囲を拡張。
- ポートフォリオ算出の安定化
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックすることでゼロ除算を回避。
  - calc_position_sizes: 価格欠損や不正値（<=0）を安全にスキップし、不正な割当を避ける処理を追加。
- ログハンドラの重複登録防止
  - setup_logging は既存ハンドラを flush/close してから削除し、二重登録を回避。

### Security
- 機密トークン取り扱い方針
  - config_setup の出力テンプレート・ウィザードで .env に機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE_TOKEN 等）を記述する点を明記し、.env を Git にコミットしないよう注意書きを追加。

### Notes / Implementation details
- PAPER_FILL_MODE: paper trading 時の MockBrokerClient の fill_mode を環境変数で指定可能。許容値は "instant" / "partial" / "never" / "reject"。不正値は ValueError で検出。
- validate_config の --strict: 警告を FAIL 扱いにできるため、本番導入前の厳密チェックに利用可能。
- process_priority: psutil が提供する OS 固有定数に依存しないよう getattr フォールバック、権限不足時は警告を出して処理を継続。
- Paper verification: レポートは稼働率・注文統計・リスク却下数・API レイテンシ（avg/max/P95）を出力し、指定閾値に基づき PASS/FAIL を判定する。

---

（この CHANGELOG はコードベースの内容から推測して作成したものです。実際のコミット履歴と整合させるには git log 等の履歴情報を使用して追補してください。）