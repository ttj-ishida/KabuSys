# Changelog

すべての重要な変更は Keep a Changelog に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※ 以下は提供されたコードベースの内容から推測して作成した初期リリースの変更履歴です。

## [Unreleased]


## [0.1.0] - 2026-04-18
初回リリース — 基本的な自動売買／検証基盤を実装しました。

### 追加 (Added)
- 実行・監視用起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper 用 SQLite を使用し MockBrokerClient を利用する挙動をサポート。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境管理
  - config.py: Settings クラスを実装。環境変数から各種設定値（DB パス、API トークン、ログレベル、監視閾値など）を取得・検証するプロパティを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を起点）を検出し、.env/.env.local を読み込む機能を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサ強化: export 形式、クォート文字列（エスケープ処理含む）、インラインコメント取り扱いなどに対応する堅牢なパーサを実装。

- 設定ツール / 検証ツール
  - config_setup.py: 対話式の .env 作成／更新ウィザードを追加（入力補助・既存値再利用・シークレットマスキングなど）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の有無・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ存在確認・config/*.yaml の存在とパース（PyYAML があれば内容検証）・本番環境向けガードをチェック。--strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合のフォールバック処理あり。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: 発注株数計算 (risk_based / equal / score) 、単元株丸め、個別上限・アグリゲート上限（利用可能現金を超える場合はスケールダウン）ロジックを実装。cost_buffer を考慮した保守的なコスト見積りを実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。ログレベルは引数 > 環境変数 > デフォルト の順で決定。
  - utils/process_priority.py: プロセス優先度（high/normal/low）を OS に応じて設定する set_process_priority を追加。Windows / POSIX (Linux/Mac/FreeBSD) に対応し、権限不足などでは警告を出して安全にフォールバック。CPU affinity を設定する set_cpu_affinity も実装。

- 解析／検証ツール
  - tools/paper_verification_report.py: Paper Trading の結果検証レポート生成ツールを追加。稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）などを集計し、閾値に基づいて PASS/FAIL を判定する。CLI から期間指定および DB パス指定が可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用）。

- 研究用ファクター計算（下地）
  - research/factor_research.py: モメンタム等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照して計算する方針。モメンタム計算関数 calc_momentum のインターフェースと定数を用意（実装の一部は継続中）。

- パッケージメタ
  - __init__.py にバージョン (0.1.0) を設定し、主要サブパッケージを __all__ でエクスポート。

### 変更 (Changed)
- なし（初回リリースのため新規実装中心）

### 修正 (Fixed)
- 環境変数の不正値に対する安全なフォールバックを実装
  - MONITOR_POLL_INTERVAL が不正値のときはデフォルト 60 秒にフォールバックして警告を出力。
  - PAPER_FILL_MODE の値検証を導入し、不正な値は ValueError を発生させる（早期検出）。
  - Settings.env / log_level の検証を追加し、不正値は ValueError で通知。

- ログ出力の扱い改善
  - cron や Task Scheduler などからの起動で扱いやすいように stdout を StreamHandler に使用（stderr ではなく stdout に出力）。

- DB 初期化の冪等性
  - init_monitoring_db を複数箇所から呼ぶ設計にして、存在確認・作成を保証（冪等）。

### 注意点 / 既知の制限 (Known issues)
- research/factor_research.py の一部実装が途中（ファイル末尾に未完の記述あり）。ファクター計算ロジックの完成が必要。
- position_sizing の価格欠損（price が 0.0）時の扱いに TODO コメントあり。将来的に前日終値などのフォールバック価格を導入することを想定。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後の利用環境でプロジェクトルートが特定できない場合は自動ロードがスキップされる。

### セキュリティ (Security)
- なし

---

参考: 各モジュールの主な使用方法（コード内 docstring より）
- 実行: python -m kabusys.run_execution
- 監視: python -m kabusys.run_monitoring
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]