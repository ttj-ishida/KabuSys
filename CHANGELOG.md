# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはコードベースからの推定に基づき作成されています。

## [0.1.0] - 2026-04-18

初期リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を追加。

### 追加 (Added)
- パッケージ基本情報
  - バージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全終了。
    - 監視は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用して DB 初期化を行う。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を利用する想定。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）／pid ファイル制御、デーモンスレッドで engine.run_session を実行し、フラグ検知で安全停止。

- 設定・環境管理
  - config.py
    - 環境変数／.env の自動読込機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - 複雑な .env パース実装（export プレフィックス、引用符・バックスラッシュ、インラインコメントの扱い）。
    - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / ログ等をプロパティとして管理。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証、PAPER_TRADING_SQLITE_PATH、PID / Kill-flag 関連設定を追加。
    - KABUSYS_ENV の検証（development / paper_trading / live）。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット項目はマスクして表示。デフォルト値や選択肢の提示、保存確認の実装。
    - .env の読み込み/書き込みロジックを提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合は）パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーにセットする。
    - ログレベル解決順およびログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ファイル出力に失敗した場合はコンソールのみで継続。

  - utils/process_priority.py
    - プラットフォームに依存しないプロセス優先度設定（"high"/"normal"/"low"）を提供。
    - Windows は psutil の優先度クラス、POSIX 系は nice 値で設定。アクセス権限不足時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を加味して特定セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは 1.0 にフォールバックして警告）。

  - portfolio/position_sizing.py
    - 発注株数決定 calc_position_sizes を追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 損切り率、リスク割合、単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した計算。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）と残余キャッシュによる四捨五入（lot 単位での再配分）ロジック。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム・Value・Volatility・Liquidity 等を想定）。
    - DuckDB を用いる設計（prices_daily / raw_financials を参照）、出力は (date, code) キーの dict リスト。
    - （ファイル途中までの実装。詳細計算は継続実装を想定。）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - DB（PAPER_TRADING_SQLITE_PATH / --db 指定可）からシステム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
    - デフォルトの閾値（稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - P95 計算、日付フィルタ（ISO8601 UTC 形式）対応。

- その他
  - monitoring/monitoring_db 初期化呼び出しを run_monitoring / run_execution から行うことで監視テーブルの冪等な初期化を担保。
  - 複数モジュールにおける停止フラグ・PID ファイル取り扱い（data ディレクトリ内ファイル）を統一的に使用。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### 既知の注意点 / 今後の改善候補
- portfolio/position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があるため、将来的に前日終値や取得原価へのフォールバックを検討する旨の TODO が存在。
  - lot_size を銘柄ごとに持たせる拡張（stocks マスタの導入）を検討。

- config._load_env_file:
  - OS 環境変数を保護する仕組みはあるが、.env の複雑なパース（引用符・エスケープ）動作は corner case が残る可能性あり。

- research/factor_research.py:
  - ファイルは途中実装。ファクター計算ロジックの完成と単体テストの追加が必要。

- process_priority / cpu_affinity:
  - 権限不足や非対応プラットフォームでの挙動は警告でスキップするが、より詳細なログやフォールバックの改善余地あり。

---

今後のリリースでは以下を想定:
- factor_research の完全実装と DuckDB を使ったパイプラインの追加
- ExecutionEngine / Broker 周り（ブローカーファクトリ・Mock の整備、注文フローのテストカバレッジ）
- モニタリング・アラート（LINE 連携）の実装および通知テスト
- 単体テスト・CI 設定の整備

（この CHANGELOG は提供されたソースコードから仕様・動作を推定して作成しています。実際のコミット履歴や変更履歴と差異がある場合があります。）