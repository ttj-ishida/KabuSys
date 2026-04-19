# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能一式を実装しました。主な追加点は以下の通りです。

### 追加（Added）
- コアランタイム / 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。環境に応じて paper_trading 用 DB を分離し、MockBrokerClient を利用可能にする。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - スレッドで ExecutionEngine をデーモン実行し、停止フラグで安全停止を行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用する挙動を明示。
    - 停止フラグ検出でループ終了、例外時はログに例外を出力して次ポーリングへ。

- 設定管理
  - config.py: .env の自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）と環境変数ラッパー Settings を実装。
    - .env/.env.local の読み込み順、OS 環境変数保護（上書き禁止）に対応。
    - 複数の設定プロパティ（J-Quants トークン、kabu API、DB パス、paper_trading 用パス、監視閾値など）を提供。
    - PAPER_FILL_MODE 等の値検証を実装（不正値は例外）。
  - config_setup: .env を対話式に生成・更新するウィザードを追加。テンプレート項目・ヘルプ表示・シークレット扱いに対応。

- 設定検証ツール
  - validate_config: 起動前に .env や config/*.yaml（存在とパース）を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パス親ディレクトリ存在チェック、live 環境向けの追加警告を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。
    - stdout（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく設定、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度変更と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac 等）の差分を吸収。権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークルール含む）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全体が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限判定で新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定、単元株丸め、max_position・aggregate cap・コストバッファ考慮のスケーリング処理を実装。

- 研究 / 指標計算枠組み
  - research/factor_research.py（モジュール骨格）
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いてモメンタム・ボラティリティ等を計算する設計（関数群の方針と定数を定義）。※ファイル末尾が未完の箇所あり（後続実装予定）。

- ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill）、送信率（send）、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を行う閾値を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。

- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更（Changed）
- なし（初回リリース）

### 修正（Fixed）
- なし（初回リリース）

### その他 / 注記
- .env パーサーはシングル・ダブルクォート内のバックスラッシュエスケープに対応し、export KEY=val 形式や行内コメントの取り扱い（クォート有無で動作を分ける）を実装しています。
- run_execution/run_monitoring はプロセス優先度を起動直後に "high" に設定するよう統一されており、権限がない環境でも安全にフォールバックします。
- 一部モジュール（research/factor_research.py）は実装途中（ファイル末尾の行が途中で終わっている箇所あり）。今後のリリースで追加実装・テスト・ドキュメント化を予定しています。

---

今後のリリースでは、strategy 実装、ExecutionEngine の詳細なテスト・ドキュメント、研究モジュールの完成、CI/テストの整備などを計画しています。