CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
形式は "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

なお、本 CHANGELOG はソースコードから推測して作成したものであり、実装意図や将来の変更により差分が生じる可能性があります。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 実行・監視ランタイム
  - run_execution.py: ExecutionEngine を起動するエントリスクリプトを追加。
    - BrokerClientFactory によるブローカークライアント生成（本番 / ペーパートレードを抽象化）。
    - ExecutionEngine を別スレッドで起動し、data/execution.pid に PID を書き、停止フラグ（data/stop_requested.flag）を検知して安全に停止。
    - Paper trading モード（KABUSYS_ENV=paper_trading）では専用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。
    - RiskManager / OrderManager / OrderRepository / Reconciler の組み立てロジックを導入。
    - RiskConfig によるリスク制限パラメータの設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、KeyboardInterrupt による終了にも対応。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。

- 設定管理・CLI
  - config.py:
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / KABUSYS_ENV 等）。
    - PAPER_FILL_MODE などの値検証（有効値チェック）を導入。
    - 環境変数未設定時に明示的なエラーを出す _require 関数を提供。
  - config_setup.py:
    - .env 作成・更新のための対話式ウィザードを追加。
    - 秘匿項目は表示をマスクし、既存 .env の読み込みと既存値の再利用に対応。
    - .env 書き込みテンプレートを提供（Git にコミットしない旨の注記を含む）。
  - validate_config.py:
    - 起動前の設定検証ツールを追加（必須環境変数・KABUSYS_ENV の妥当性・DB パス・config/*.yaml の存在とパースチェックなど）。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 内容チェックをスキップして警告を出す。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等配分にフォールバックする警告を追加。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率を評価して新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - position size 計算ロジック calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）への丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、端数処理アルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なロギング設定ユーティリティを実装。
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
    - LOG_DIR の自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プラットフォーム差を吸収するプロセス優先度設定と CPU affinity 設定を実装（psutil ベース）。
    - Windows / POSIX(nice) に対応。失敗時は警告を出してスキップ。

- 解析・レポート
  - tools/paper_verification_report.py:
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db（環境変数で上書き可）。
  - research/factor_research.py:
    - ファクター計算モジュールの骨組み（モメンタム等）を実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。

Changed
- .env の読み込み仕様
  - .env のパースを拡張して以下に対応:
    - export KEY=val 形式
    - シングル・ダブルクォートで囲まれた値とバックスラッシュエスケープの正しい処理
    - クォートなし値のインラインコメント扱い条件の改善（'#' の前がスペース/タブ の場合にコメントと判定）
  - 自動ロード順序を明確化: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

Fixed
- ロバストネスの改善
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール出力 (stdout) にフォールバックするように調整。
  - psutil ベースの優先度設定や CPU affinity 設定はアクセス権や未実装例外を捕捉して警告を出すようにしてクラッシュを防止。
  - validate_config では PyYAML が無い環境でも graceful に動作し、適切な警告を出すように変更。
  - DB 初期化: init_monitoring_db を run_execution/run_monitoring 起動時に呼び、監視テーブルの存在を保つ（冪等）。

Security
- 環境変数取り扱い
  - config_setup の出力では .env を Git にコミットしない旨の注意を追加。
  - 必須シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は取得に失敗した場合に明示的なエラーを投げる実装で安全な初期化を促す。

Notes / Design decisions
- 監視モジュールは「環境にかかわらず本番の sqlite_path を使用する」設計になっている点に注意（意図的な分離ルール）。
- Paper trading は実運用 DB と分離されるよう配慮されている（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- 一部モジュール（factor_research など）は処理の骨組みや SQL/計算方針を定義しており、詳細実装（完全な算出クエリ、追加のエラーハンドリング等）は今後拡張が想定される。

Acknowledgements
- 本 CHANGELOG は現行ソースコードから推測して作成しています。実際の変更履歴やリリースノートが別途存在する場合はそちらを優先してください。