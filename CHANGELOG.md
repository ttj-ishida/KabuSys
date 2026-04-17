# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。

## [0.1.0] - 2026-04-17

初回公開リリース。

### 追加
- コア設定・環境読み込み
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env ファイルのパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを実装し、アプリケーション全体で利用する設定値（DB パス、API トークン、環境種別等）を提供。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH 等の環境変数をサポート。PAPER_FILL_MODE の有効値チェックを追加（instant / partial / never / reject）。

- CLI ツール
  - config_setup: 対話式ウィザードで .env を初期作成/更新する `python -m kabusys.config_setup` を追加。主要設定項目（KABUSYS_ENV、J-Quants、kabu API、DB パス、LINE 設定等）を対話的に登録できる。
  - validate_config: 起動前に .env と config/*.yaml を検証する `python -m kabusys.validate_config` を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ確認、YAML パース検証（PyYAML がインストールされている場合）を行う。`--strict` で警告を失敗扱いにできる。
  - tools/paper_verification_report: ペーパートレード用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定する（閾値はファイル冒頭に定義）。コマンド例:
    - `python -m kabusys.tools.paper_verification_report`
    - `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`
    - DB パスは --db または PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）。

- 実行用スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。起動時にプロセス優先度を "high" に設定。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と完全分離する。MockBrokerClient を利用するフローを組み込む想定（BrokerClientFactory 経由）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。停止制御はプロジェクト内 data/stop_requested.flag により行う。

- ポートフォリオ構築ライブラリ
  - portfolio_builder: シグナル候補抽出（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
  - risk_adjustment: セクター集中上限の適用（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier: bull/neutral/bear）を実装。未知レジームは警告のうえ 1.0 でフォールバック。
  - position_sizing: 各銘柄の発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、銘柄毎上限・aggregate cap（available_cash 超過時のスケーリング）や cost_buffer（手数料・スリッページ予備）を考慮した配分を行う。残差配分は lot 単位で再配分するロジックを実装。

- 研究用モジュール
  - research/factor_research: DuckDB 接続によりファクター（Momentum: 1M/3M/6M/MA200乖離、Volatility: ATR20, avg turnover, volume ratio 等）を計算する関数を追加。prices_daily テーブルを用いる設計。結果は (date, code) をキーとした dict リストで返す。

- ユーティリティ
  - utils/process_priority: psutil を用いたプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows / POSIX（Linux, macOS, FreeBSD）間の差分を吸収し、権限不足や未対応環境では警告を出してスキップする。

### 変更
- パッケージメタ情報:
  - パッケージ初期バージョンを __version__ = "0.1.0" に設定。

### 修正（設計上の注意点・既知の制約）
- apply_sector_cap 内で価格が 0.0 の場合にエクスポージャーが過少見積もられる可能性があることをコメントで明示。将来的には前日終値や取得原価等のフォールバックを検討する旨を記載。
- position_sizing で将来的に銘柄別単元株対応（lot_map）へ拡張する TODO を記載。
- set_process_priority / set_cpu_affinity は権限不足やプラットフォーム未対応時に例外を握りつぶしてログ警告で処理継続する仕様（安全重視）。

### セキュリティ
- .env の生成スクリプトで「.env を絶対に Git にコミットしない」旨の注記を追加。
- 必須機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）を Settings 経由で必須チェックし、未設定時は ValueError を投げる（起動前に validate_config で検出することを推奨）。

### ドキュメント / 使用上のメモ
- 起動前にまず .env を作成し、`python -m kabusys.validate_config` で設定検証を行うことを推奨。
- ペーパートレード実行時は KABUSYS_ENV=paper_trading を設定すると、発注実行はモックブローカーに切り替わり、DB は PAPER_TRADING_SQLITE_PATH で指定した別 DB に記録されるため本番 DB と分離される。
- 監視プロセス（run_monitoring）は MONITOR_POLL_INTERVAL で間隔を変更可能（1 秒以上の整数）。不正な値を指定した場合はデフォルト 60 秒にフォールバック。
- 停止制御はリポジトリ直下の data/stop_requested.flag（run_monitoring/run_execution で参照）により行う。起動時に停止フラグが立っていると起動を抑止する挙動がある。

### 既知の未実装 / TODO
- prices 等のフォールバック価格ロジック（apply_sector_cap の price 欠損対処）。
- position_sizing の銘柄毎 lot_size マップ対応。
- research/factor_research の追加ファクター・正規化ユーティリティ（kabusys.data.stats との連携は設計に含むが未表示部分あり）。
- config/*.yaml のテンプレート生成スクリプト（validate_config は存在しない場合に警告を出すが、生成スクリプトの実行方法を案内しているだけ）。

----

今後のリリースでは、上記 TODO の対応、テストカバレッジの拡充、Execution/Monitoring のより詳細なエラーハンドリングやランタイムメトリクス出力の強化を予定しています。