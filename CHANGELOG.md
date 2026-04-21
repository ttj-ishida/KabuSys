# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースから推測できる変更点・機能を記述したものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクトの data/stop_requested.flag ファイルを検知するとループを終了する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring 用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して接続・初期化。
    - DuckDB 接続を併用。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag によりエンジンを停止・起動抑止。
    - 実行用 PID ファイルを data/execution.pid に作成/利用する仕組み（Engine に渡す）。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序をサポート（OS 環境変数を保護）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定 等）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - settings オブジェクトをエクスポート（Settings インスタンス）。

- 設定ユーティリティ・CLI
  - validate_config.py
    - .env や config/*.yaml を起動前に検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL のバリデーション、DB パスの親ディレクトリ存在チェック、YAML ファイルのパースチェック（PyYAML 利用）。
    - KABUSYS_ENV=live の場合の注意喚起チェック（LINE通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定等）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - インタラクティブな .env 作成 / 更新ウィザードを追加。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を提供。
    - 既存 .env の読み込み、シークレット値のマスク表示、保存確認、.env の書き込みロジックを実装。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしコンソールのみで継続。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を行うユーティリティを追加。
    - set_process_priority(level) により high/normal/low の優先度を設定（権限不足時は警告を出してスキップ）。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity(cpu_count) を追加（利用不可・権限不足時は警告を出してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap（当日売却予定銘柄除外、"unknown" セクターは制限除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear マップ、未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing の実装を追加（risk_based / equal / score の allocation_method）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積もり、残差処理（lot 単位での追加配分）等を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標を集計して検証レポートを出力する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルトの閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ（--from, --to）と --db オプションをサポート。

- research/factor_research.py
  - ファクター計算モジュールの実装着手（モメンタム等の計算ロジックの設計・定数定義を追加）。duckdb 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。

- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を追加。
  - portfolio パッケージのエクスポートと tools パッケージのひな型を追加。

### 変更 (Changed)
- .env 読み込み挙動の堅牢化
  - .env 行パーサは引用符付き値のバックスラッシュエスケープやインラインコメントの扱いに対応。export プレフィックス対応。
  - _load_env_file() は既存 OS 環境変数を保護するため protected 引数を導入。
- ロギング設定
  - コンソール出力は stderr ではなく stdout を使用するよう変更（タスクスケジューラ/cron での出力リダイレクトを考慮）。
- DB 初期化
  - 実行/監視起動時に監視テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等に動作）。

### 修正 (Fixed)
- 不正な環境変数値に対するフォールバック
  - MONITOR_POLL_INTERVAL が非整数または 0 以下の場合、警告を出してデフォルト（60 秒）にフォールバックする処理を追加。
  - PAPER_FILL_MODE が不正な値の場合は ValueError を送出して早期検出。
  - LOG_LEVEL / KABUSYS_ENV が不正な値のときに検出してわかりやすいエラーメッセージを出すバリデーションを追加。
- プロセス優先度設定失敗時に例外を投げず警告でスキップするようにして起動の堅牢性を向上。

### 既知の制限 (Known Issues)
- research/factor_research.py はファイル末尾が途中で切れている（calc_momentum の実装は途中）。完全実装は次リリース予定。
- 一部の TODO（例: price 欠損時のフォールバック価格、銘柄別 lot_size のサポート）が存在するため、実運用前に追加の堅牢化が必要。
- set_cpu_affinity とプロセス優先度設定は権限やプラットフォームに依存し、すべての環境で同じ結果が得られるわけではない（失敗時は警告でスキップ）。

---

今後のリリースでは以下を予定しています（推定）:
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出）
- position_sizing のさらに詳細な検証とユニットテスト追加
- ロギング・監視まわりの通知（LINE 連携）実装
- 単体テスト・CI の整備

---