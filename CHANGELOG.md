# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。  
バージョン番号はパッケージの __version__ に合わせています。

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-25

### Added
- 基本構成と起動スクリプトを実装
  - run_execution.py: 実行エンジン（ExecutionEngine）起動用スクリプト。  
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を通じて本番 / モックのブローカークライアントを生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による安全停止をサポート。
    - 実行時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。  
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。KeyboardInterrupt を捕捉して安全終了。
- 設定管理・自動 .env 読み込み
  - config.py: 環境変数/.env/.env.local をプロジェクトルートから自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
    - .env パースは export プレフィックス、シングル/ダブルクォート、インラインコメント（空白の前にある #）等を考慮した堅牢な実装。  
    - Settings クラスを提供し、アプリケーションで使用する各種設定値（DB パス、API トークン、閾値、環境判定フラグ等）をプロパティとして取得可能。  
    - PAPER_FILL_MODE の検証、paper_sqlite_path、PID / kill flag パス、監視閾値（CPU/メモリ/ディスク）などをサポート。
- 設定支援ツールと検証ツール
  - config_setup.py: 対話式ウィザードで .env の作成・更新を支援。必須項目/任意項目/マスク入力等を備える。保存時にテンプレートで .env を出力。  
  - validate_config.py: .env と config/*.yaml の基本チェックを行う CLI。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を実施。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。  
    - stdout への StreamHandler と 日次ローテートの TimedRotatingFileHandler（logs/<app>.log）をルートロガーに設定。  
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックあり。  
    - ログレベルは引数 > 環境変数 > デフォルト の順で解決。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を提供。  
    - Windows（psutil の定数を使用）と POSIX（nice 値）の差分を吸収し、失敗時は警告を出してスキップする堅牢な実装。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア配分を実装。スコアが全て 0 の場合は等金額へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中の上限フィルタ（apply_sector_cap）と市場レジームに応じた乗数計算（calc_regime_multiplier）を実装。既存ポジションと当日売却予定を考慮したセクターエクスポージャー計算を行う。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position と aggregate の上限管理、available_cash に応じたスケールダウン（端数処理ロジック含む）を備える。
  - portfolio パッケージで上記関数群を公開。
- 研究用ファクターモジュール（骨格）
  - research/factor_research.py: DuckDB 接続を受けて各種ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計を実装。モメンタム計算（1M/3M/6M、MA200乖離など）に関する定数と説明を含む設計。DuckDB の prices_daily / raw_financials を参照する前提。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper trading 用 SQLite を解析して検証レポートを生成する CLI。  
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg, max, P95）等。  
    - 閾値（デフォルト）: 稼働率 >= 99.0%、fill >= 90%、send >= 95%、P95 latency <= 200 ms。  
    - 日付フィルタ（--from / --to）と DB パスの指定（--db または PAPER_TRADING_SQLITE_PATH）に対応。
- パッケージ初期化
  - kabusys/__init__.py にてバージョンを "0.1.0" として定義。

### Changed
- 初回リリースのため該当項目なし。

### Fixed
- 初回リリースのため該当項目なし。

### Security
- 初回リリースのため該当項目なし。

---

注記:
- run_monitoring は監視用 DB（sqlite_path）を環境にかかわらず本番用パスで初期化する設計になっています。paper_trading 用に監視を分離したい場合は設定の見直しが必要です。  
- 一部モジュール（research/factor_research.py 等）は設計コメントおよび計算ロジックの骨格を含みます。将来的な拡張で DuckDB クエリや追加のファクターを実装する想定です。