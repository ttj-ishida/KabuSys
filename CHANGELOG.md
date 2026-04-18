# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン情報はパッケージ定義 (src/kabusys/__init__.py) に基づきます。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーション骨格を実装。
  - パッケージ名: KabuSys（日本株自動売買システム）。
  - バージョン: 0.1.0

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを提供。
    - KABUSYS_ENV に応じて paper_trading モード用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory によりブローカークライアントを抽象化（paper_trading 時は MockBrokerClient を使用する想定）。
    - エンジンの PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）による制御をサポート。
    - ExecutionEngine の依存コンポーネント組み立て（OrderRepository、OrderManager、RiskManager、Reconciler 等）を行う。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（環境に依存せず監視 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）で安全にループを終了可能。

- 設定管理・初期化
  - config.py
    - .env 自動ロード機構（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env/.env.local の読み込み順序と上書き制御（OS 環境変数保護）。
    - 複雑な .env パーサ（export、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスにより環境変数をプロパティとして提供（J-Quants、kabu API、DB パス、監視閾値、環境判定等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定、閾値やファイルパスのデフォルト値を定義。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を実装。
    - 各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を補助的に入力可能。
    - .env の読み取り／書き込み、シークレットのマスク表示、保存確認をサポート。
    - 生成される .env に関する注意（Git にコミットしない等）を出力。

  - validate_config.py
    - 起動前チェック用 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - 本番環境 (KABUSYS_ENV=live) 向けの追加ガード（LINE 通知設定の未設定警告、KILL_FLAG_CLEAR_ON_START の危険性警告）。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR の解決順や、ハンドラの二重登録防止のため既存ハンドラのクリア処理を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティ。
    - set_process_priority(level) により "high"/"normal"/"low" を概念的に扱う。
    - set_cpu_affinity(cpu_count) によりカレントプロセスを最初の N コアにピン止め可能（対応環境でのみ実行）。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアゼロ時は等金額にフォールバックし警告出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき候補を除外するロジック。既存ポジションの時価評価を考慮し、"unknown" セクターは除外対象としない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告のうえ 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
    - リスクベースの算出、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash に基づくスケーリング）をサポート。
    - cost_buffer により手数料・スリッページを保守的に見積もるロジックを実装。
    - 価格欠損時のスキップやログ出力、将来的な価格フォールバックの TODO コメントを含む。

- 分析 / リサーチ機能（DuckDB 経由）
  - research/factor_research.py（部分実装）
    - モメンタム、MA200 乖離、ATR、流動性系などのファクター計算に着手。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。
    - 設計方針や定数（horizon、ウィンドウ長等）を定義。関数インターフェース（calc_momentum 等）を準備。
    - （注）ファイル末尾が一部切れているため実装完了部分と未完了部分が混在。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、API レイテンシ (avg/max/P95) 等を算出し、閾値による PASS/FAIL を判定。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプションをサポート。
    - P95 計算、各種 SQL 集約クエリ、N/A ハンドリングを実装。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

### 変更 (Changed)
- n/a（初回リリースのため既存リポジトリからの変更履歴はありません）

### 修正 (Fixed)
- n/a

### 既知の注意点 / 制限
- research/factor_research.py が途中で切れており、一部関数実装が未完（ファイル末尾の不完全な状態）。本リリースでは設計と一部処理を導入しているが、完全なファクター計算のテストが必要。
- apply_sector_cap: price_map に欠損（0.0）がある場合にエクスポージャーが過少評価される懸念があり、将来的に前日終値や取得原価などのフォールバック導入を予定。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム非対応時にスキップされる設計（安全志向）。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後や特殊なインストール状況で検出できない場合は自動ロードをスキップする（KABUSYS_DISABLE_AUTO_ENV_LOAD で明示的に無効化可能）。
- ログファイル用ディレクトリ作成に失敗した場合はファイル出力が無効化されストリーム出力のみとなる。

### セキュリティ (Security)
- n/a

---

今後の予定（例）
- research/factor_research.py の完全実装と単体テスト追加。
- ExecutionEngine / SystemMonitor の結合テスト（paper_trading と live 両対応）。
- 個別銘柄ごとの単元株情報導入（lot_size の銘柄別対応）。
- config/*.yaml のスキーマ検証とより詳細な起動時チェック。

もし CHANGELOG に追加したい事項や日付・表現の変更希望があれば教えてください。