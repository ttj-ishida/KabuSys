CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。
この CHANGELOG は提示されたコードベースの内容から推測して作成したものであり、実際の変更履歴やリリース日とは異なる可能性があります。

Unreleased
----------

- なし

[0.1.0] - 初回リリース（推測）
----------------------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用の SQLite（data/paper_trading.db）に記録するよう分離。
  - run_monitoring.py: SystemMonitor をポーリングする監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知、PID ファイル取り扱い、例外時のログ保護を実装。

- 設定・環境周り
  - config.py: 環境変数/ .env の自動読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD に依存しない自動ロード。
    - .env の行パーサで export 形式、クォート文字列、エスケープ、インラインコメントルールをサポート。
    - 多数の設定プロパティ（DB パス、ペーパートレード用パス、PID/killフラグ、監視閾値、ログレベル、環境判定など）を提供。PAPER_FILL_MODE のバリデーション等を含む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。秘密設定のマスク表示、既存 .env の読み込み、保存プレビューを提供。

  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML があれば内容も検証）、--strict モード（警告を FAIL 扱い）を実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）をルートロガーに統一して設定するユーティリティを追加。ログディレクトリ自動作成、作成失敗時のフォールバック処理、環境変数/引数によるログレベル・出力先選択をサポート。
  - utils/process_priority.py: プラットフォームを吸収するプロセス優先度設定と CPU affinity 設定を追加（Windows / POSIX 対応）。権限不足や未対応 OS では警告ログにフォールバック。

- モニタリング DB 初期化
  - monitoring.monitoring_db モジュール（起動スクリプトから使用）により、監視用テーブルの初期化を起動時に保証（冪等）。run_execution と run_monitoring が起動時に init を呼ぶ。

- Execution 系の構成コンポーネント（起動スクリプトで組み立て）
  - BrokerClientFactory によるブローカークライアント生成（環境により Mock / 実ブローカー切替）。
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み合わせてエンジン起動。RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）や初期ポートフォリオ値の初期化に broker.get_available_cash() を使用。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等ウエイト・スコア加重配分（スコアが全て 0 の場合は警告して等ウエイトにフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用（既存保有からのセクター比率計算、sell_codes 除外対応、"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。損切り率・許容リスク率・単元株丸め（lot_size）・max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap（スケーリング）処理を実装。余りの配分は fractional remainder に基づいて lot 単位で追加。

- Research / Tools
  - research/factor_research.py: DuckDB を用いたファクター（モメンタム/MA200/ATR/出来高等）計算モジュールの骨子を追加（prices_daily / raw_financials テーブル参照、Zスコア正規化を前提）。（実装途中の関数が含まれる。）
  - tools/paper_verification_report.py: ペーパートレード用 SQLite から集計して検証レポートを出力するユーティリティを追加。稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均/最大/P95）を計算し、閾値（稼働率 99%、fill 90%、send 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を行う。コマンドライン引数 --from / --to / --db をサポート。

- パッケージ情報
  - __init__.py にて __version__="0.1.0" を定義し、主要モジュール（data/strategy/execution/monitoring）を __all__ に追加。

Changed
- 新規プロジェクトの初期構成として多くの新機能を追加（上記 Added を参照）。

Fixed
- .env 読み込みの堅牢化
  - export 付き行・クォート内のバックスラッシュエスケープ・インラインコメント処理を明確化し、実世界の .env パターンへの耐性を向上。
- ロギング初期化の堅牢化
  - ログディレクトリ作成失敗時にファイルハンドラ生成をスキップして標準出力のみで継続するフォールバックを実装。既存ハンドラの安全なクローズ処理を追加。
- プロセス優先度設定のクロスプラットフォーム対応
  - Windows / POSIX の差分を吸収し、権限不足時に警告でスキップするように変更。

Removed
- なし（初回リリースのため該当なし）。

Deprecated
- なし。

Security
- なし（今回のコードから推測できるセキュリティ関連のリリースノートはありません）。

Notes / 実装上の注意（開発者向け）
- run_monitoring と run_execution は監視用 stop フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを行うため、デプロイ時は data ディレクトリの権限・存在を確認してください。
- Settings による環境変数取得は未設定時に ValueError を送出するものと任意取得するものが混在します。起動前に validate_config.py で設定検証を実行することを推奨します。
- research/factor_research.py の一部は実装途中の様子が見られます（ファイル末尾で関数定義が途中で終わる等）。ファクター算出ロジックは DuckDB テーブルスキーマ（prices_daily / raw_financials）に依存します。
- position_sizing.calc_position_sizes の aggregate cap スケールダウンロジックは lot_size 単位で切り捨て・再配分を行います。将来的に銘柄毎の lot_size をマスタ化するための TODO が残されています。

以上。必要であれば、特定ファイルごとの詳細な変更点や開発者注記（未実装 FIXME/TODO の一覧）を追記します。どの程度の粒度で記載するか指示してください。