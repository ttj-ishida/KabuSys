# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
バージョン付けは semantic versioning を想定しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、モニタリング/検証ツール、設定管理 CLI などを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用フラグファイル data/stop_requested.flag を監視して安全に終了。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して DB を初期化。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper-trading 用の専用 SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを作成（paper_trading 時には MockBrokerClient を利用する想定）。
    - 実行中の PID 管理、停止フラグ検出でエンジンを安全に停止するロジックを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定ロード・管理
  - src/kabusys/config.py
    - 環境変数／.env 自動読み込み機構を追加（プロジェクトルートは .git または pyproject.toml から検出）。
    - .env のパースは export プレフィックス、クォート文字、エスケープ、インラインコメント等を考慮した堅牢な実装。
    - 多数の設定プロパティを提供（DB パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE など）。
    - Settings クラス経由で設定の型変換・バリデーションを行う（env の妥当性確認、PAPER_FILL_MODE の有効値チェックなど）。

  - src/kabusys/config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - デフォルトの設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, Kill Switch 設定等）をガイド付きで生成・更新可能。
    - .env を書き出す際に注意書き（Git にコミットしない等）を含める。

  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の基本的な検証を行う CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の値検査、DB パスの親ディレクトリ確認、YAML の存在 & パース検査（PyYAML が利用可能な場合）、本番環境向けの追加警告を実装。
    - --strict オプションで警告も失敗扱いにするモードを提供。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告を出す。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションを基にセクター比率を計算してブロック）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear 対応、未知レジームはフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size による丸め、max_position_pct、max_utilization、コストバッファを考慮した aggregate cap スケーリング）。
    - スケールダウン時の端数配分を再現性を保って行う実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージエクスポート。

- 解析・研究モジュール
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20 等）、流動性指標を計算する関数を実装。
    - prices_daily / raw_financials テーブルのみを参照する純粋関数設計。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity 固定を行う set_cpu_affinity を追加。権限制約時は警告を出してスキップ。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite ログから検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシなどを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - デフォルトの閾値を設定（稼働率 >= 99%、fill_rate >= 90% 等）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Usage highlights
- モニタリングは意図的に「環境に依存せず本番 sqlite_path を使う」よう設計されています。監視 DB とペーパートレード DB を分離したい場合は run_execution の paper_trading モードを利用してください。
- .env 自動読み込みはデフォルトで有効。テストや特殊用途で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env ウィザードで生成された .env は Git にコミットしないでください（config_setup.py に注意書きあり）。
- process_priority や CPU affinity の設定は権限や OS に依存します。失敗しても警告を出して続行する設計です。
- Paper Trading レポートの閾値はツール内定数で定義されています。プロジェクトの実運用基準に合わせて変更してください。

---

将来的なリリースでは、ブローカー実装の詳細、ExecutionEngine の追加設定、より詳細な監視/アラート機能、strategy 実装との統合などを想定しています。