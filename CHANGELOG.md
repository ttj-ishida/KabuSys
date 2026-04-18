# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルでは、リポジトリの現状（コードベースから推測できる機能群）を元に v0.1.0 リリースの内容をまとめています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 起動スクリプト（CLI）
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する設計。
    - DuckDB と SQLite の接続初期化を行い、SystemMonitor.check_once() を定期実行。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用（本番 DB と分離）。
    - BrokerClientFactory を用いてブローカークライアントを生成（モック含む）。
    - エンジンはデーモンスレッドで実行され、停止フラグを検知して安全に停止。
    - 実行中の PID を data/execution.pid に記録する設計をサポート。

- 環境設定・検証関連の CLI
  - config_setup: 対話式ウィザードで `.env` を生成 / 更新する CLI を追加。
    - J-Quants / kabu API / DB パス / LINE 通知設定など主要項目を扱う。
    - シークレット項目は表示をマスクして扱う。
  - validate_config: `.env` と config/*.yaml の検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV、LOG_LEVEL、DB パスの存在などをチェック。
    - `--strict` フラグで警告を FAIL 扱いにできる。
    - PyYAML が無い場合は YAML 検証をスキップする（警告出力）。

- 環境変数ロード機能の改善
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、`.env` / `.env.local` を安全にロード。
  - .env パーサーを実装し、以下に対応:
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行でのインラインコメント処理（直前がスペース / タブ の場合のみ）
  - OS 環境変数を保護して .env の上書きを制御する仕組みを導入（protected keys）。

- 設定取得ラッパー
  - `kabusys.config.Settings` クラスを追加し、環境変数をプロパティ経由で型変換・検証して提供。
    - J-Quants / kabu API / LINE / DB パス / 監視閾値 / KABUSYS_ENV / LOG_LEVEL 等を扱う。
    - `PAPER_FILL_MODE` の許容値チェック、`KABUSYS_ENV` と `LOG_LEVEL` のバリデーション、`paper_sqlite_path` のプロパティ等を実装。
    - `settings = Settings()` をモジュールレベルで用意。

- ロギング & プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログディレクトリ自動作成・失敗時のフォールバック（コンソールのみ）に対応。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト（INFO）。
  - process_priority: psutil を用いたプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- 実行系コンポーネント（概要）
  - ExecutionEngine 周りの組立て（OrderRepository, OrderManager, RiskManager, Reconciler, EngineConfig）を利用する起動フローを追加。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）をサンプルとして定義。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選択（タイブレーク用 signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を確認して候補から除外するロジック。
      - 未知セクター ("unknown") は上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投入倍率（bull/neutral/bear）を返す。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元株（lot_size）丸め、銘柄ごとの上限、aggregate cap によるスケールダウン、残差による追加配分（fractional remainder を利用）を実装。
      - cost_buffer による保守的なコスト見積りをサポート。

- 研究・解析モジュール（着手）
  - research.factor_research の骨格を追加（DuckDB 接続を受ける設計、モメンタム / ボラティリティ / Value 系の計算方針をコメントで明記）。
    - モメンタム計算（calc_momentum）の実装開始（関数シグネチャ、定数）が含まれる。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db、--db オプションで上書き可能。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義している。

### Changed
- データベースの扱い
  - 監視（monitoring）機能は KABUSYS_ENV に依らず production sqlite_path（settings.sqlite_path）を使用するよう明示。
  - 実行（execution）は paper_trading 環境の場合に専用 DB（paper_sqlite_path）を使用し、本番 DB と分離する設計へ。

- ロギングの挙動
  - コンソール出力は stdout を使用するよう統一（cron 等で stdout/stderr を一本化する運用を想定）。
  - 日次ローテーション（30 日保持）をデフォルトに設定。

### Fixed
- .env のパースとロードに関する堅牢性向上
  - quote 内のエスケープ、export プレフィックス、インラインコメント処理を強化。
  - .env の読み込みで OS 環境変数を保護する機能を導入（意図せぬ上書きを回避）。

### Deprecated
- なし（初期リリースのため該当なし）。

### Removed
- なし（初期リリースのため該当なし）。

### Security
- なし（特に報告する脆弱性は検出されていないが、シークレット扱いの変数は .env を Git にコミットしない旨の注意喚起を出力するツールを含む）。

## Known issues / TODO
- portfolio.position_sizing:
  - 価格（price）が欠損（0.0）の場合、現状は単純にスキップしてしまいエクスポージャーが過少評価され得る。将来的に前日終値や取得原価をフォールバック価格として扱う検討が必要（コード中に TODO コメントあり）。
- research.factor_research:
  - ファイル末尾が途中で切れており（calc_momentum の実装が途中）、完全実装は未完。DuckDB を用いた各ファクター算出ロジックの実装が残っている。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合は、意図的に console のみで継続する仕様だが、運用時にファイル出力が得られない可能性に注意。
- process_priority / set_cpu_affinity は権限や OS に依存するため、環境によって期待通り動作しないことがある（警告でスキップする実装）。

---

この CHANGELOG は、提供されたソースコードをベースに推測してまとめたものです。実際の変更履歴やリリースノートは、リポジトリの履歴（git commit）やリリース管理ポリシーに基づいて調整してください。