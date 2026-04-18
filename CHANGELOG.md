# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

なお本ファイルは、与えられたコードベースの内容から実装・挙動を推測して作成しています。

## [Unreleased]

- 今のところ未リリースの変更はありません。

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加項目は以下の通りです。

### Added
- 全体
  - パッケージ初期化（src/kabusys/__init__.py）とバージョン定義（`__version__ = "0.1.0"`）。
  - DuckDB と SQLite を併用するデータアクセス基盤を採用（環境変数でパス指定可能）。

- 実行・監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - BrokerClientFactory により本番／ペーパートレード用ブローカークライアントを生成。
    - Paper Trading（KABUSYS_ENV=paper_trading）時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - RiskManager のデフォルト設定を定義（max_position_pct、max_utilization、rate_limit など）。
    - 実行中は PID ファイルを書き、外部の停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - エンジンは別スレッドで実行し、停止フラグ検知時に engine.stop() を呼び出す。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを一元管理。
    - init_monitoring_db による監視 DB 初期化、DuckDB との接続、停止フラグ検知、例外ハンドリングを実装。

- 設定管理
  - config.py: Settings クラスを追加。
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env 行パーサーはクォートやバックスラッシュエスケープ、コメント処理を考慮した堅牢な実装。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE など）の取得・検証ロジック。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証。
    - convenience プロパティ（is_live / is_paper / is_dev 等）。

  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力のマスク表示、既存 .env の読み込みと更新をサポート。
    - .env ファイルのテンプレート書き出し（Git 管理不可の注意書き付き）。

  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - 本番環境 (KABUSYS_ENV=live) 向けのガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションにより警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群: DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抽出（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等額配分とスコア加重配分（全スコアが 0 の場合は等額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限に基づく候補除外（売却予定銘柄の除外、"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告とともに 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注数計算、単元（lot_size）丸め、per-stock 上限・aggregate cap、コストバッファ（手数料・スリッページ想定）を考慮したスケーリング。

- ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - 既存ハンドラの二重登録防止処理、LOG_LEVEL / LOG_DIR の解決順、ファイル出力失敗時のフォールバック。
  - utils.process_priority:
    - psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows / POSIX(nice)）と CPU affinity 設定。
    - サポート外 OS や権限不足時は警告を出して安全にスキップ。

- 監視・検証ツール
  - tools.paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を抽出して検証レポートを生成（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など）。
    - デフォルト閾値を定義し、PASS/FAIL 判定を行う CLI（--from/--to/--db オプション）。

- 研究（研究用モジュール）
  - research.factor_research: DuckDB を使ったモメンタム等ファクター計算モジュール（モメンタム計算の設計と定数を実装。関数は prices_daily / raw_financials に依存）。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して、監視用テーブルの初期化を起動スクリプト内で保証（冪等）。

### Changed
- ログ出力
  - コンソール出力を stderr ではなく stdout に揃える方針に変更（logging_setup で明示的に stdout を使用）。

### Fixed
- .env パーサーの堅牢化
  - シングル/ダブルクォート内のエスケープ、インラインコメント処理、`export KEY=...` 形式のサポートなどを実装し、実運用での .env 記述差異に耐えるよう改善。

### Security
- 機密情報の扱い
  - config_setup においてシークレット項目（トークン・パスワード）はマスク表示。`.env` のコミット禁止を README/コメントで明示。

### Notes / Limitations
- research.factor_research は設計に沿った初期実装を含むが、外部依存（prices_daily のスキーマ等）により実行環境での追加検証が必要です（コード断片が途中で終わっている箇所があるため、今後完成を予定）。
- 一部の機能（ExecutionEngine、SystemMonitor、BrokerClient など）は本ログに含まれる起動・組立てコードを示すが、実行時の挙動は各コンポーネントの実装に依存します。
- ローカル環境や CI でのテスト実行時は、`.env` 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を用意しています。

---

以上がコードベースから推測して作成した初期リリース（0.1.0）の変更履歴です。必要であれば各ファイルごとの差分想定や、今後のリリース案（修正予定・機能追加予定）も作成できます。どのレベルの詳細が必要か教えてください。