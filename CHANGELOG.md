# CHANGELOG

すべての notable な変更は Keep a Changelog の慣習に従って記載します。  
フォーマット: https://keepachangelog.com/（日本語簡易版）

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

### Added
- 基本機能の初期実装を追加（初回リリース）。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を利用するよう分離。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag を検知して行う。
  - 環境設定・検証ツール
    - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（秘密値マスク表示、.env の読み書き対応）。
    - validate_config.py: 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在チェック等）。--strict オプションで警告を FAIL 扱いにできる。
  - 運用ツール
    - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツールを追加（稼働率・注文成功率・送信率・レイテンシ等を集計、閾値による PASS/FAIL 判定を出力）。P95 計算機能を含む。
  - ポートフォリオ構築関連モジュール（純粋関数群、DB 参照なし）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）・等重配分・スコア加重配分を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）・市場レジーム乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score の allocation_method、単元丸め、aggregate cap スケーリング、cost_buffer 対応）を実装。
    - portfolio/__init__.py: 上記関数を公開。
  - リサーチ / ファクター計算（骨格）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、MA、ATR、出来高等を想定）。DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計。
  - ユーティリティ
    - utils/logging_setup.py: 統一的ロギング設定を提供。コンソール（stdout）と TimedRotatingFileHandler（日次、30世代保持）をルートロガーへ設定。LOG_DIR 作成失敗時はファイル出力をスキップし、コンソールのみで継続するフォールバックを実装。
    - utils/process_priority.py: Windows/Linux/macOS を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。psutil の例外を捕捉してフォールバックする。
    - config.py: 環境変数読み込み・Settings クラスを実装。.env 自動ロード機能（プロジェクトルート自動検出）を追加し、.env と .env.local 読み込み順序をサポート。エスケープ・引用符付き値・export プレフィックス・インラインコメント等に対応した .env パーサを実装。各種設定プロパティ（DB パス、paper_trading の分離設定、閾値、PID/kill flag パス等）を提供。
  - DB 初期化フック
    - 各起動スクリプトから monitoring テーブルの存在を保証する init_monitoring_db 呼び出しを行うよう統一（冪等に実装されている想定）。

### Changed
- なし（初回公開のため変更履歴はなし）

### Fixed
- なし（初回公開）

### Security
- なし

### Notes / 実装上の挙動（重要点）
- run_monitoring は KABUSYS_ENV にかかわらず "本番" の sqlite_path（Settings.sqlite_path）を使用する設計になっている点に注意。対照的に run_execution は paper_trading 環境で専用の paper_sqlite_path を使用して本番 DB と分離される。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップする。自動ロード自体は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- logging_setup はログディレクトリ作成やファイルハンドラ作成に失敗した場合でも動作を継続し、コンソール出力のみでログを残すよう安全にフォールバックする。
- process_priority や set_cpu_affinity は権限不足や環境依存の実装差異に対して警告を出しつつ処理をスキップする安全設計。
- Paper Trading の検証レポートはデフォルトで data/paper_trading.db を参照する（環境変数/PAPER_TRADING_SQLITE_PATH または --db オプションで上書き可能）。
- position_sizing の集約スケーリングは cost_buffer（手数料・スリッページ見積り）を考慮して算出し、単元株（lot_size）単位で丸める。価格欠損時はスキップされる実装上の挙動に注意。

---

（今後のリリースでは変更内容を Unreleased セクションに追加し、リリース時に日付を付与してください。）