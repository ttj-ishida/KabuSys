# CHANGELOG

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
- リリース日は YYYY-MM-DD 形式で記載しています。

なお、本CHANGELOGはコードベースから機能実装・振る舞いを推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

追加
- 基本パッケージ構成とバージョン
  - パッケージバージョンを設定: `kabusys.__version__ == "0.1.0"`。
- 設定管理
  - 環境変数/`.env` 自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml から探索して `.env` / `.env.local` を自動読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って自動読み込みを無効化可能。
    - `.env` のパースはコメント、クォート、`export KEY=val` 形式、インラインコメント等に対応。
  - Settings クラスを提供し、アプリケーション設定（DBパス、APIトークン、環境フラグ等）を型付きプロパティで取得可能。
    - `KABUSYS_ENV` のバリデーション（development / paper_trading / live）。
    - `PAPER_FILL_MODE` の検証（instant/partial/never/reject）。
    - 各種デフォルト値（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `LOG_LEVEL` 等）。
- CLI/ユーティリティ
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式に `.env` を作成・更新するウィザードを提供。
    - デフォルト値・選択肢・シークレット入力のサポート、書き込みテンプレートを実装。
    - 生成後に `python -m kabusys.validate_config` で検証することを推奨。
  - 設定検証ツール（kabusys.validate_config）
    - 起動前に `.env` と `config/*.yaml`（存在する場合）を検証する CLI。
    - 必須環境変数の有無チェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML があれば）を実行。
    - `--strict` オプションで警告も失敗扱いにできる。
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
    - `data/paper_trading.db` 等の Paper Trading 用 SQLite DB からレポートを生成。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）に対応。
- ランタイム起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - プロセス優先度を高（"high"）に設定してから起動。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - Broker クライアントをファクトリ経由で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: プロジェクトの `data/stop_requested.flag` を監視し、検知時にエンジン停止。
    - PID ファイル書き込み（`data/execution.pid` デフォルト）対応。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - プロセス優先度を高（"high"）に設定してから起動。
    - 監視用は環境にかかわらず本番の `sqlite_path` を使用して監視テーブルを初期化。
    - DuckDB 接続と SQLite 接続を確立し、SystemMonitor を用いてポーリング実行。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効な値はデフォルトにフォールバック。
    - 停止フラグファイル（`data/stop_requested.flag`）を検知してループ終了、KeyboardInterrupt も考慮。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 選定・重み付け（portfolio_builder）
    - BUY シグナルのソートと上位 N 抽出（select_candidates）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコアが0のとき等金額にフォールバック。
  - リスク調整（risk_adjustment）
    - セクター集中の上限チェックと候補除外（apply_sector_cap）。既存保有の時価評価を用いて判断、`unknown` セクターは上限対象外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）：bull/neutral/bear マップ（未定義は警告と 1.0 フォールバック）。
  - 株数決定・ロット丸め（position_sizing）
    - allocation_method に応じた株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、コストバッファを考慮した安全なスケールダウンロジックを実装。
    - 価格欠損等の扱い（価格が取得できない場合はスキップ）や端数の追加配分ロジックを備える。
- ロギング・プロセスユーティリティ（kabusys.utils）
  - 統一ロギング設定（kabusys.utils.logging_setup）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - 既存ハンドラの二重設定防止、ログレベル・ログディレクトリの解決順を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度と CPU affinity 設定（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を先頭 N コアに固定するユーティリティを提供。権限不足や未対応 OS の場合は警告を出してスキップ。
    - 例外（AccessDenied 等）に対して安全にフォールバックする実装。
- 研究用モジュール（kabusys.research）
  - ファクター計算モジュールの骨格（factor_research）を実装（duckdb 経由で price/financials を参照して Momentum/Value/Volatility/Liquidity を算出する方針）。
    - モメンタム計算のための定数と設計方針を記載（関数インターフェースを準備）。※コードは一部（途中）まで実装。

改善
- デフォルトのファイル・ディレクトリ構成を明確化
  - デフォルト DB / ログ / PID / stop flag のパスを統一して `data/` / `logs/` 配下に設定。
- 安全対策
  - 監視・実行起動時にプロセス優先度を最初に設定し、重要処理の優先度を確保。
  - `.env` の自動読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

ドキュメント（コード内コメント）
- 各モジュールに設計方針、使用方法、引数仕様の詳細な docstring とコメントを追加。
  - run_* スクリプトの使い方、config_setup/validate_config の利用手順、portfolio モジュールの設計参照ドキュメント（PortfolioConstruction.md 等）についての注記を含む。

注記 / マイグレーション
- .env の管理
  - .env は絶対に Git にコミットしないことを README 等で徹底してください（config_setup もその旨をコメント付きで書き出します）。
- 起動スクリプト
  - 監視プロセスは MONITOR_POLL_INTERVAL（秒）でポーリング間隔を設定できます。不正値はデフォルト 60 秒にフォールバックします。
  - 実行エンジンは `KABUSYS_ENV=paper_trading` の場合に paper_trading 専用 SQLite を使用し、本番データとは分離されます。運用時は環境変数を適切に設定してください。
- 本番環境注意点
  - `KABUSYS_ENV=live` の場合、LINE 通知トークン等の設定が未設定だと警告となります。`KILL_FLAG_CLEAR_ON_START` は本番では `0` を推奨します。

既知の制限 / TODO
- factor_research の関数は一部未完（コメントに設計方針あり）。DuckDB 上の SQL 実装部分は今後追加予定。
- 一部の価格欠損時のフォールバック（前日終値や取得原価）については TODO コメントあり。将来的な拡張検討が必要。

---

（必要に応じてリリース履歴を追加してください）