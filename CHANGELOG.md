# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このドキュメントは Keep a Changelog のフォーマットに従っています。  

## [0.1.0] - 2026-04-19

初回公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、監視・実行ランナー、設定関連ツールなどを含みます。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全停止処理を実装。
    - 監視用 DB（SQLite）および DuckDB へ接続し、monitoring テーブルの初期化を行う。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する旨を明記。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の際は MockBrokerClient 等を用いて paper_trading 専用 DB（デフォルト: data/paper_trading.db）に記録。実運用 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知によるセッション停止、実行用 PID ファイル管理のサポート。
    - スレッドで ExecutionEngine.run_session を実行し、メインスレッドで停止フラグ監視を行う。

- 設定管理 / CLI
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得（duckdb/sqlite パス、KABUSYS_ENV 判定、paper_trading 用設定など）。
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）を実装。`.env` / `.env.local` の読み込み順と OS 環境変数の保護機構をサポート。
    - `.env` のパースでクォート文字・エスケープ・コメントなどに対応する堅牢な実装。
    - PAPER_FILL_MODE 等の検証（有効値チェック）を実装。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 秘匿項目のマスク表示、選択肢チェック、既存 .env の読み込みと保存機能を提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML ファイル存在チェック（PyYAML の有無に応じて挙動を切り替え）、本番向けの追加ガード等を実装。
    - `--strict` オプションで警告も FAIL として扱う機能を追加。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリ共通のログ設定ユーティリティを追加。コンソール出力（stdout）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順をサポートし、ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）差を吸収したプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity を設定する set_cpu_affinity を追加（利用不可時は警告を出してスキップ）。

- ポートフォリオ構築モジュール（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコアが全て 0 の場合のフォールバック挙動を実装（等分配にフォールバックして warning）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加。既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは上限適用外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ見積もり）、スケールダウン時の端数処理（lot 単位での追加配分）を実装。

- Execution 周りの骨組み（実装参照）
  - run_execution で使用される BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の参照（ファイル構成を想定）を組み立てるコードを追加し、RiskConfig のデフォルトパラメータを定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。

- 監視 / 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均/最大/P95）などを集計して人間可読なレポートを出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。

- リサーチ（ファクター）モジュール（骨組み）
  - research/factor_research.py
    - モメンタム等のファクター計算機能（calc_momentum 等）のスケルトンと定数を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。複数の期間定数（1M/3M/6M/MA200/ATR 等）を定義。

### 変更 (Changed)
- ロギングの挙動
  - StreamHandler を stdout に固定（stderr ではない）し、Task Scheduler/cron からのリダイレクトを考慮した設計に変更（ログ統一のため）。

- .env 読み込みの安全化
  - OS 環境変数を保護する `protected` 機構を導入し、`.env.local` による上書き時も OS の既存設定を上書きしないように実装。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを正しく処理するよう改善。

- DB / ファイルハンドラのフォールトトレランス
  - ログディレクトリ作成やログファイルハンドラ生成に失敗した場合でもコンソールログのみで継続動作するよう変更（起動失敗の回避）。

### 注意事項 (Notes)
- run_monitoring は環境にかかわらず Settings().sqlite_path（通常は本番監視 DB）を用います。監視用 DB を開発環境と分離したい場合は Settings の環境変数（SQLITE_PATH 等）を適切に設定してください。
- run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を使用します。paper_trading を利用する際は PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE を確認してください。
- config.py の Settings は必須環境変数を参照すると例外を投げます。CI やユニットテストで自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- factor_research モジュールはファクター計算の骨組みを提供していますが、完全な処理実装は今後の拡張を想定しています（現時点で一部未完）。

---

今後のリリース案内: バグ修正、テスト追加、ExecutionEngine / BrokerClient の具体的実装、ファクター計算の完成、パフォーマンス改善（並列化等）を予定しています。