# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 形式に準拠しています。  
このファイルはコードベースからの推測に基づき作成しています。

## [0.1.0] - 2026-04-18

### Added
- 基本的なアプリケーション構成を追加
  - パッケージのバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き、停止フラグ検出、監視用 DB 初期化（monitoring 用テーブル）等に対応（src/kabusys/run_monitoring.py）。
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、paper_trading 時の専用 DB（data/paper_trading.db）使用、Broker クライアントの生成、ExecutionEngine のスレッド実行/停止ロジック、PID/停止フラグ管理を実装（src/kabusys/run_execution.py）。
- 設定管理
  - Settings クラスを追加して環境変数から設定を取得・検証する仕組みを提供（src/kabusys/config.py）。
    - 自動 .env ロード機能（プロジェクトルート検知: .git または pyproject.toml を基準）を導入（`.env`, `.env.local` の読み込み、OS 環境変数の保護機構あり）。
    - 各種プロパティを提供（J-Quants トークン、kabu API password / base URL、LINE トークン/ユーザ、DuckDB/SQLite パス、paper_trading 用 DB パス、監視閾値、環境名/ログレベル判定など）。
    - `PAPER_FILL_MODE` のバリデーション（有効値: instant/partial/never/reject）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェック。
- 設定支援 CLI
  - config_setup: .env を対話的に生成・更新するウィザードを追加（既存値の読み込み、シークレットのマスク表示、デフォルト値、保存確認など）（src/kabusys/config_setup.py）。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パス/親ディレクトリのチェック、config/*.yaml の存在とパース（PyYAML が無い場合はスキップ）を行い、--strict モードで警告をエラー扱いにできる（src/kabusys/validate_config.py）。
- ロギング・プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ/ログレベル解決ロジック、ハンドラ二重登録防止、ファイル書き込み失敗時のフォールバックを実装（src/kabusys/utils/logging_setup.py）。
  - process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を提供。psutil を利用しつつ権限・未対応 OS に対するフォールバックを実装（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築・リスク・ポジション算出
  - portfolio.portfolio_builder: シグナル選定（スコア降順、タイブレーク）と等金額・スコア重み配分関数を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - portfolio.risk_adjustment: セクター集中上限を適用する機能（当日売却予定を除外可能）、市場レジームに応じた投下資金乗数の算出（bull/neutral/bear）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - portfolio.position_sizing: 重み・候補・価格・現金・制限値から銘柄別の発注株数を計算するロジックを実装。risk_based / equal / score の配分方式に対応し、単元株（lot_size）への丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積もりなどをサポート（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証レポート
  - tools.paper_verification_report: Paper Trading 用 SQLite DB から各種指標（稼働率・注文成功率・送信率・レイテンシ等）を集計し、閾値に基づく PASS/FAIL レポートを生成する CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - P95 の計算、期間フィルタ、各テーブル存在チェックに対するフォールバックを実装。
- 研究用ファクター計算（開始）
  - research.factor_research: モメンタム等のファクター計算モジュールを追加（モメンタム指標計算の実装を開始。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）（src/kabusys/research/factor_research.py、実装は継続中）。

### Changed
- run_execution / run_monitoring の振る舞い
  - run_monitoring は環境に関係なく（KABUSYS_ENV に依らず）本番用の sqlite_path を使用して監視データを保持する仕様を明示。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite を使用することにより本番 DB と分離するよう設計。
- ロギングの振る舞い
  - logging_setup は stdout を StreamHandler に使用する（stderr ではなく stdout）。ログローテーションは日次・30世代保持に設定。

### Fixed
- 環境変数ロードの堅牢化
  - .env パーサで `export KEY=val` 形式、クォート文字列内のバックスラッシュエスケープ、インラインコメント取り扱い、クォートなしの場合のコメント認識などを考慮することで .env 読み取り精度を向上（src/kabusys/config.py）。
- 設定検証時のエッジケースハンドリング
  - validate_config が PyYAML 非インストール時に YAML 検査をスキップし警告を出すよう改善（src/kabusys/validate_config.py）。

### Notes / Known issues / TODOs
- position_sizing: 将来的に銘柄ごとの単元（lot_size）を stocks マスタに持たせる拡張を想定する TODO コメントあり。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる点について注記（将来的に前日終値等へのフォールバックが必要）。
- calc_regime_multiplier: 未知のレジーム値は警告を出して 1.0 でフォールバックする実装となっている（安全側のフォールバック）。
- logging_setup: ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する設計。
- process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームでは警告を出して安全にスキップする実装。
- research.factor_research は実装途中（ファイル末尾で切れている箇所がある）ため、完全なファクター計算のユニットは今後整備予定。

### Security
- 環境変数（シークレット系）は `.env` の取り扱いに関する注意喚起（config_setup のヘッダで .env を絶対に Git にコミットしないことを明記）。

---

以上がコードから推測した変更点です。必要であれば、各項目をさらにファイル単位で分解した詳細な変更履歴（diff ベース想定）を作成できます。どのレベルの詳細が必要か指示ください。