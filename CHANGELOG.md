CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — and is maintained in
SemVer format.

- リリース日: 2026-04-20
- バージョン: 0.1.0

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティと CLI を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合はモックブローカ（MockBrokerClient）を使用し、ペーパートレード用 SQLite（data/paper_trading.db）と本番 DB を完全に分離。
    - プロセス優先度を "high" に設定し、PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
    - BrokerClientFactory によるブローカークライアントの抽象化、OrderRepository/OrderManager/RiskManager/Reconciler 組み立てを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出でループを終了、例外発生時にログを残して次ポーリングへ継続。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを導入。環境変数からアプリケーション設定を取得するプロパティ群を提供（J-Quants、kabu API、LINE、DBパス、監視閾値、KABUSYS_ENV 等）。
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。読み込み順序: OS 環境 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース機能を強化（export KEY=、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
    - PAPER_FILL_MODE（paper trading の約定挙動）や PAPER_TRADING_SQLITE_PATH の検証・既定値を提供。
    - 各種閾値（CPU/MEM/DISK）や PID / Kill flag 関連設定プロパティを実装。
    - settings = Settings() のインスタンスをエクスポート。

- 設定検証 / ウィザード
  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリ確認、YAML パース検証（PyYAML がない場合はスキップして警告）、本番時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援する CLI を追加。
    - シークレット入力のマスク表示、選択肢・デフォルト表示、既存 .env の読み込み、書き込みテンプレート（コメント付き）を提供。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーにセットアップ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
    - 環境変数 LOG_LEVEL / LOG_DIR による上書き、引数での上書きに対応。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を提供。psutil を利用し、権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有に基づいて特定セクターが上限（max_sector_pct）を超えている場合、新規候補を除外するロジック。unknown セクターは除外対象外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジック（calc_position_sizes）を実装。allocation_method (risk_based / equal / score) 対応、単元株（lot_size）丸め、per-position と aggregate の上限、cost_buffer を考慮したスケーリング（投資額が available_cash を超える場合に安全にスケールダウンし、残余で端数調整）を提供。

- 解析 / レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill / send）、リスク却下数、レイテンシ（avg / max / P95）を集計して Pass/Fail 判定（既定閾値あり）を行う。DB パスは環境変数 PAPER_TRADING_SQLITE_PATH もしくは --db オプションで指定可能。
    - P95 計算ユーティリティ、日付フィルタ、欠損テーブルに対する堅牢な例外処理を備える。

- パッケージ情報
  - __init__.py にて __version__="0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Known limitations
- research/factor_research.py はモメンタム算出などの実装を開始しているが、ファイル末尾（calc_momentum の実装途中）で切れているため未完成箇所あり。今後のリリースで完了予定。
- apply_sector_cap 内の価格欠損（price == 0.0）によりエクスポージャーが過小評価されて除外が漏れる可能性がある旨を TODO コメントで注意。フォールバック価格の導入を検討中。
- position_sizing の将来的拡張として、銘柄別の lot_size をマスタに持たせる案をコメントとして残している。

開発者向け
- 環境変数の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。配布後やテストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログは標準出力 (stdout) にも出力されるため、cron / Task Scheduler 等でのリダイレクト運用に適しています。

--- 
今後の予定（短期）
- factor_research の完了（全ファクター実装と正規化）
- SystemMonitor / ExecutionEngine 周辺のテスト追加と頑健性向上
- docs にインストール・運用手順を追加

（この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴・設計意図と異なる場合があります。）