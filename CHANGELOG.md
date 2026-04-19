KEEP A CHANGELOG
全ての変更は https://keepachangelog.com/ja/ に準拠しています。

# [Unreleased]

# [0.1.0] - 2026-04-19
最初の公開リリース。システム全体の起動スクリプト、環境設定、監視・実行ユーティリティ、ポートフォリオ構築ロジック、補助ツール類を実装しました。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は環境 (KABUSYS_ENV) に関わらず本番用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ・PID ファイル対応。エンジンはデーモンスレッドで起動、フラグ検知で安全停止。

- 環境設定 / 検証
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順を実装。OS 環境変数は保護され、上書き制御あり。
    - 複雑な .env パースを実装（export プレフィックス、クォート内のエスケープ、インラインコメント処理等）。
    - 各種設定項目（DB パス、LINE トークン、paper_trading 用設定、閾値等）をプロパティとして定義。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。シークレット項目はマスクして表示、保存時の注意喚起を出力。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML の有無を考慮）などを備える。
    - --strict オプションで警告も FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーへ設定する統一ユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順を明記。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows / POSIX(nice) 対応）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（指定コア数に固定、未対応環境は警告してスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして Warning を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を実装（apply_sector_cap）。当日売却予定銘柄の除外対応、unknown セクターは上限適用外。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）超過時のスケールダウン、残差処理による追加配分ロジックを実装。
    - cost_buffer による保守的なコスト見積りをサポート。

- 解析 / 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを追加。P95 レイテンシ、稼働率、注文成功率/送信率、リスク却下数などを集計し PASS/FAIL を判定可能。
    - CLI オプション --from/--to/--db をサポート。デフォルト DB は data/paper_trading.db。

- 研究用モジュール（骨組み）
  - research/factor_research.py
    - DuckDB 接続を受け取りファクター（Momentum, Value, Volatility, Liquidity）を計算するための設計と一部実装（定数、API）を追加（本リリースではモジュールが途中まで実装）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- データベースの取り扱い方針
  - 監視（monitoring）は環境に依らず production sqlite_path を使用する仕様に明確化。
  - Execution は paper_trading 環境で専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
- ログ出力先
  - コンソール出力は stderr ではなく stdout を採用（Task Scheduler / cron での取り扱いを考慮）。
- .env 読み込み優先度
  - OS 環境変数 > .env.local > .env の順で解決する仕組みを採用し、既存 OS 環境変数を保護するロジックを実装。

### Fixed
- MONITOR_POLL_INTERVAL の不正値処理
  - 0 以下や整数変換失敗時は警告を出してデフォルト値（60 秒）にフォールバックするよう改善。
- .env パーサの安定性向上
  - export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメント処理を正しく扱うように修正。
- process_priority の堅牢化
  - 未対応 OS や権限不足時に例外を落とさず警告でスキップする挙動に修正。
- validate_config の YAML チェック
  - PyYAML 未導入環境への配慮を追加（存在しない場合は YAML 検証をスキップして警告を出す）。

### Security
- 機密情報の扱い
  - config_setup のウィザード・出力はシークレット項目をマスク表示するように実装。`.env` ファイルの Git コミット禁止を README 風に強調して出力。

### Notes / TODO
- research/factor_research.py は未完（calc_momentum 等の実装が途中）。今後のリリースでファクター計算ロジックを完成させる予定。
- position_sizing の価格欠損（price == 0）時のフォールバック（前日終値や取得原価）については TODO コメントあり。より堅牢な価格フォールバックを検討する。
- 将来的には銘柄ごとの単元株数をマスタ化し、lot_size を銘柄別にサポートする設計へ拡張予定。

---

もし CHANGELOG に追加してほしい詳細（例: 各ファイルごとのコミット単位、著者、関連 issue 番号など）があれば教えてください。必要に応じてリリースノートの粒度を調整します。