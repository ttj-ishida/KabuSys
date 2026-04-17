# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。なお、本ファイルはコードベースから推測して作成した変更履歴です。

※ 日付はリリース想定日です。

## [Unreleased]

### 追加
- 監視・実行エントリポイントを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag により検知。監視は環境に依らず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db デフォルト）を使用し、MockBrokerClient（BrokerClientFactory を介して）で完全に分離される。起動・停止は data/stop_requested.flag と pid ファイルで管理。

- 設定読み込み・管理
  - config.py: .env の自動読み込み機能を追加（プロジェクトルートの .env/.env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env 行のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮する堅牢な実装。Settings クラスで環境変数をラップし、各種既定値・検証を提供（KABUSYS_ENV / LOG_LEVEL の検証、PAPER_FILL_MODE の有効値チェックなど）。

- 設定関連 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する機能を追加。主要な設定項目とデフォルト値、シークレット扱いの項目（マスク表示）に対応。保存前の確認プロンプトを実装。
  - validate_config.py: 起動前の設定検証ツールを追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML 有り時の）パース検証、本番環境向けガードなど。--strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全てが 0 の場合は等配分へフォールバックして Warning を出力。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知のレジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出ロジックを追加（risk_based / equal / score の配分方式をサポート）。lot_size（単元株）丸め、per-stock と aggregate のキャップ、cost_buffer による保守的見積り、スケーリング・端数調整ロジックを実装。

- 解析・研究モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、流動性などの骨組み）を追加。prices_daily テーブルを参照し、MA200、1/3/6 か月リターン、ATR、20日平均売買代金などを算出するクエリと振る舞いを実装。

- ユーティリティ
  - utils/process_priority.py: Windows/Linux/macOS を考慮したプロセス優先度設定ユーティリティを追加。psutil を利用し、優先度変更や CPU affinity 設定を試行。権限不足や未対応 OS の場合は安全にスキップして警告出力。

- モニタリング DB 初期化フック（init_monitoring_db）や SystemMonitor / ExecutionEngine 周りの組み立てロジックを想定して各モジュールを統合。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成を追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定（閾値はソース内定義）で出力。--from/--to/--db オプションにより期間・DB を指定可能。

### 変更
- パッケージ初期化に __version__ = "0.1.0" を設定（初回公開想定）。

### 修正
- なし（初期リリース想定）

### 破壊的変更
- なし

## [0.1.0] - 2026-04-17

初回リリース（推定）。上記 Unreleased の内容を本リリースに含む想定。

### 追加
- 起動スクリプト: run_monitoring.py, run_execution.py
- 設定管理: config.py, config_setup.py, validate_config.py
- ポートフォリオ構築: portfolio/（portfolio_builder, risk_adjustment, position_sizing）
- 研究用ファクター計算: research/factor_research.py（DuckDB クエリ実装）
- 実行ユーティリティ: utils/process_priority.py
- 検証ツール: tools/paper_verification_report.py
- パッケージ初期化: src/kabusys/__init__.py

### 注記 / 既知の挙動
- .env の自動読み込みはプロジェクトルートが特定できた場合のみ行われ、OS 環境変数を優先する（.env.local は .env を上書き）。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- run_monitoring は監視用途の sqlite_path を常に本番設定から参照する設計。run_execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して DB を分離する。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム差分を考慮して安全にスキップされる（警告ログ）。

---

参考（設計上の想定機能）
- 設定検証 CLI は PyYAML が無い場合に YAML 検証をスキップするが、その旨を警告する。
- portfolio モジュールの関数は副作用を持たない純粋関数として設計されており、テストや再利用を想定。
- paper_verification_report は各種閾値（稼働率・成功率・P95 レイテンシ等）に基づく PASS/FAIL 判定を行い、運用検証に役立つ出力を提供する。

もし希望があれば、各リリースノートをもっと細かく（ファイル単位の変更点や実装上の注意点、既知のバグや TODO）に分けて追記します。