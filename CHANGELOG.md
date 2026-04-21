# KEEP A CHANGELOG

すべての変更は "Keep a Changelog" の慣例に従って記載します。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

- （無し）

## [0.1.0] - 初期リリース
初回リリース。以下の主要機能・ユーティリティを実装しています。

### 追加
- 全般
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として追加。
  - コマンドライン実行やスクリプトから利用できる複数の起動スクリプト／CLI を実装。

- 環境設定 / 設定管理
  - 環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env ファイルのパース機能を独自実装（コメント、クォート、`export KEY=val` 形式、インラインコメント等に対応）。
  - .env の読み込み時に OS 環境変数を保護する仕組みを実装（override と protected の概念）。
  - Settings クラスを実装し、アプリ設定（DB パス、KABUSYS_ENV、LOG_LEVEL、Paper Trading 関連設定、閾値など）をプロパティ経由で取得・バリデーション。
  - PAPER_FILL_MODE の値検証（有効値: "instant"/"partial"/"never"/"reject"）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- 設定ウィザード / 検証ツール
  - `kabusys.config_setup`：対話式ウィザードで .env を初期作成・更新する CLI を実装（シークレット表示はマスク、既存値の再利用、保存確認）。
  - `kabusys.validate_config`：起動前検証ツールを実装。必須環境変数確認、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの存在確認（親ディレクトリ）、config/*.yaml の存在確認と（PyYAML がある場合は）パース検証を行う。`--strict` オプションで警告をエラー扱いにできる。
  - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や Kill Switch の自動クリア設定に関する警告）。

- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ開始スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き（デフォルト 60 秒、0 以下はデフォルトへフォールバック）。
    - 監視用 DB は環境に関わらず本番用 sqlite_path を使用して初期化（init_monitoring_db）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live による分岐想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - RiskManager のデフォルト設定（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20）を提供。
    - 起動時・実行中に停止フラグ検知で安全に停止処理を行う。PID ファイル出力先指定。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`
    - ルートロガーに StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler を設定するユーティリティを実装。
    - ログディレクトリ自動作成、ファイルハンドラ作成失敗時はコンソールのみで継続するフォールバック。
    - ログレベル・ログディレクトリの解決順をドキュメント化。
    - デフォルトで 30 日分を保持。
  - `kabusys.utils.process_priority`
    - Windows と POSIX を吸収したプロセス優先度設定関数 `set_process_priority(level)` を実装（high/normal/low）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装（利用不可時は警告してスキップ）。
    - 権限不足等で失敗した場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、タイブレークに signal_rank）を実装。
    - 重み計算 `calc_equal_weights`（等金額）と `calc_score_weights`（スコア正規化、全スコア 0 の場合は等配分にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap` を実装（unknown セクターはキャップ無視）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（"bull":1.0 / "neutral":0.7 / "bear":0.3、未知レジームは 1.0 + 警告）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック `calc_position_sizes` を実装。
    - allocation_method に応じた挙動（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金 available_cash を超える場合のスケールダウン）、cost_buffer による保守的コスト見積り、残余キャッシュを用いた端数配分アルゴリズムを実装。
    - 価格欠損に対するログ出力・スキップ処理を備える。

- リサーチ / ファクター計算（分析）
  - `kabusys.research.factor_research` を追加。モメンタム等のファクター計算を行う設計（DuckDB 接続を受けて prices_daily / raw_financials を参照する方針）。モメンタム計算関数（calc_momentum）の実装開始。  
    注: ファイルは一部実装途中で終了しているため、今後の拡張・完成が必要。

- ツール / レポート
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用の検証レポートを生成する CLI を実装。
    - 検証指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 閾値（デフォルト）を定義し、PASS/FAIL 判定を行ってレポートを標準出力に出力。
    - P95 算出ユーティリティ、日付フィルタ（ISO8601 UTC 文字列化）、DB 存在チェック等を実装。

### 変更点（設計上の注記）
- 監視（monitoring）は環境に関わらず本番用 sqlite_path を使用する設計（意図的に監視データを一元化）。
- 起動時にプロセス優先度を "high" に設定するコードが各起動スクリプトの最初に挿入されている（パフォーマンス優先の設計上の決定）。
- ログは標準出力（stdout）を優先して出力する実装（cron / scheduler での取り扱いを意図）。

### 既知の制限 / 今後の作業
- `kabusys.research.factor_research` の一部実装が途中で終わっている（続きの実装が必要）。
- position_sizing 等で価格が欠損（0.0）だった場合の補完（前日終値等）について TODO コメントあり。将来的にマスタデータの拡張を想定。
- 一部モジュール（例: ブローカークライアントの具象実装、monitoring.system_monitor 等）の詳細実装は本差分に含まれていないため、統合テストが必要。

---

（補足）この CHANGELOG はコードベースの内容から推測してまとめたものです。実際の変更履歴やリリースノートを反映する場合は、コミット履歴やリリース管理の情報に基づいて適宜調整してください。