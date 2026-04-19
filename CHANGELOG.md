# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
（内容は提示されたコードベースから推測して作成しています）

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、開発向けツールを追加。

### 追加 (Added)
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB から分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - 停止制御用フラグファイル（data/stop_requested.flag）および PID ファイル(data/execution.pid) による起動/停止制御を実装。
    - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する（監視用 DB を保証）。
    - 同様にプロセス優先度を "high" に設定し、停止フラグでループを終了する仕組みを実装。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。

- 設定・環境読み込み
  - config.Settings を追加。
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - 必須/任意の環境変数のラッパー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - デフォルト値・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH のサポート）、PID/kill flag 等のパス設定。
    - 関連プロパティ: is_live, is_paper, is_dev。

- 設定管理・検証ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 各設定項目の説明、デフォルト値、シークレットマスク表示、保存確認までを実装。
    - .env ファイルの読み書きユーティリティを提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの追加警告等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - stdout への StreamHandler（stderr ではなく stdout を使用）と、日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成のフォールバック（失敗時はファイルハンドラを無効化してコンソールのみで継続）。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils.process_priority を追加。
    - Windows/Linux/macOS に対して優先度（high/normal/low）の設定を抽象化。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を提供（コア固定）。
    - 権限不足などの例外は警告にフォールバックする安全設計。

- ポートフォリオ構築・リスク管理（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順でシグナルを選別。タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等分にフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 1 セクターの上限比率を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 にフォールバック（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じて各銘柄の発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン機構を実装。
    - cost_buffer を用いた保守的コスト見積と、残差に基づく追加配分アルゴリズムを実装。
    - 不足データ（価格欠損）時はスキップしログ出力。

- 研究・分析モジュール雛形
  - research.factor_research の実装開始（モメンタム/MA/ATR 等の計算方針と定数を定義）。（未完の関数が存在）

- 開発ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI を追加。
    - Paper Trading SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）からデータを集計。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数等。
    - Pass/Fail 判定基準（デフォルト閾値: uptime >= 99.0%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200 ms）に基づく判定を出力。
    - 日付フィルタ（--from/--to）対応。

- パッケージ初期設定
  - __init__.py にてバージョン __version__ = "0.1.0" を設定し、主要モジュールを __all__ で公開。

### 変更 (Changed)
- .env 自動読み込みの挙動
  - プロジェクトルートを .git / pyproject.toml で探索する方法を採用し、カレントワーキングディレクトリに依存しない自動ロードを実現。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

- .env パーサの拡張
  - export キーワードの扱い、クォート内でのバックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - クォートなしの値では '#' の前に空白がある場合のみコメントとして扱うなど細かな振る舞いを定義。

- validate_config の出力/判定ロジック
  - PyYAML が存在しない場合は YAML 検証をスキップし警告を出すフォールバックを追加。

### 修正 (Fixed)
- ログ設定の冪等性を実現
  - setup_logging で既存ハンドラを flush/close してから削除し、二重設定を防止。

- プラットフォーム差分の安全処理
  - process_priority/set_cpu_affinity で権限不足・未対応 API へのアクセスを捕捉し警告にフォールバックするように修正（クラッシュ防止）。

### 既知の制限 / 注意点 (Known issues / Notes)
- research.factor_research の一部実装が未完（calc_momentum の途中で切れているなど）。実データ計算ロジックは継続実装が必要。
- position_sizing における price が欠損（0.0）の場合の扱いについて TODO コメントあり：前日終値や取得原価でのフォールバックを将来的に検討。
- monitoring の sqlite 接続は「環境にかかわらず本番 sqlite_path を使用」する設計になっているため、テスト実行時は意図的に DB パスの上書きが必要な場合がある。
- .env の自動読み込みはプロジェクトルート検出に依存しており、配布後のパッケージ環境で想定通りに動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化して外部で環境変数を管理することを推奨。

---

この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴や意図した変更点と差異がある場合は、実際の git ログ等を参考に更新してください。