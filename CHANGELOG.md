# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳準拠）

## [Unreleased]

### Added
- 起動スクリプトを追加/整理
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag によって行う。
    - Monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使用。
  - run_execution.py を追加。ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録する。
    - エンジンは PID ファイルと停止フラグをサポート。バックグラウンドスレッドで run_session を実行して停止フラグ検知で安全に停止。
- 設定関連 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する機能を追加。
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。
- 設定管理の強化 (kabusys.config)
  - .env 自動読み込み機構を追加（プロジェクトルート自動探索、.env/.env.local の読み込み順）。
  - .env の行パーサを改善し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを導入して環境変数取得を集約（J-Quants / kabu API / DB パス / paper_trading 用設定 / 監視閾値 など）。
  - PAPER_FILL_MODE の妥当性チェック、paper_sqlite_path の追加。
  - kill/ pid/ 各種閾値（CPU/MEM/DISK）設定のプロパティ化。
- ログ・プロセスユーティリティ (kabusys.utils)
  - logging_setup.py を追加
    - ルートロガーに stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしコンソール出力のみで継続するフォールバック処理を実装。
    - ログレベル/ディレクトリの解決順序を明確化（引数 > 環境変数 > デフォルト）。
  - process_priority.py を追加
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限エラー等を安全にハンドリング。
- ポートフォリオ構築関連モジュール (kabusys.portfolio)
  - portfolio_builder.py: シグナル選定（select_candidates）と重み計算（等金額/スコア重み）を実装。
  - risk_adjustment.py: セクター集中制限 apply_sector_cap とレジーム乗数 calc_regime_multiplier を実装。
  - position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。lot_size による単元丸め、aggregate cap によるスケーリング、cost_buffer を考慮した計算を実装。
  - パッケージ __init__ で上記関数をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。paper_trading の SQLite を解析して稼働率・注文成功率・送信率・レイテンシ等のレポートを生成。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、PASS/FAIL 判定を出力。
    - --from/--to/--db オプションをサポート。
- DuckDB の統合ポイントを追加
  - 起動スクリプトから duckdb.connect を呼び、分析用 DB を共有する設計を反映（settings.duckdb_path を通して指定）。

### Changed
- ログ挙動
  - logging_setup が標準エラーではなく標準出力（stdout）に StreamHandler を張るようにした（cron/タスクスケジューラからの取り扱いを考慮）。
- DB 初期化
  - 起動時に init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）。
- 環境変数ロード順序
  - OS 環境 > .env.local > .env の優先順位を明確化。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを抑制可能。

### Fixed
- 設定パーサの堅牢化
  - .env パースでのクォート処理やエスケープ、コメント処理の不整合を修正。export プレフィックスをサポート。

---

## [0.1.0] - unreleased
（初回リリース相当の機能群をまとめたエントリ）

### Added
- プロジェクト初期リリース: 基本的な自動売買フレームワークを提供
  - 実行スクリプト: run_execution, run_monitoring
  - 設定管理: Settings クラス、.env 自動ロード、config_setup ウィザード、validate_config チェッカ
  - ロギング・プロセス制御ユーティリティ: logging_setup, process_priority
  - ポートフォリオ構築: 候補選定、重み付け、リスク調整、発注株数計算
  - Paper Trading 向け検証ツール: paper_verification_report
  - DuckDB/SQLite によるデータ保存・分析の枠組み
- パッケージメタ
  - __version__ を "0.1.0" に設定

### Notes
- 一部のモジュール（研究用ファクター計算など）は今後の拡張を想定した設計になっており、継続的に機能追加を行う予定です。
- 本リリースでは .env に機密情報（API トークン等）を保存する設計のため、.env を絶対にリポジトリへコミットしないでください（config_setup のヘッダにも明記）。

---

変更や追加機能に関する不明点や補足が必要であれば、どの部分について詳しく記載するかを教えてください。