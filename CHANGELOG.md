# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠します。

- リリースノートはコードベースから推測して作成しています。実際のリリース履歴と差異がある場合があります。

## [0.1.0] - 2026-04-24

初回リリース（推定）。以下の主要機能・改善点を含みます。

### 追加 (Added)
- CLI / 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレーディング用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動前に stop フラグ（data/stop_requested.flag）をチェックし、存在する場合は起動を中止。
    - 実行中は別スレッドでエンジンを走らせ、停止フラグ検出時に engine.stop() を呼び出して安全終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
- 設定管理
  - config.py
    - .env の自動読み込み機能（プロジェクトルート探索: .git または pyproject.toml を基準）。
    - .env / .env.local 読み込みの優先順位と OS 環境変数保護を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値 / 環境種別判定 等）。
    - PAPER_FILL_MODE の入力検証（有効値: instant|partial|never|reject）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツール。
    - デフォルト・選択肢の提示、シークレットマスク、保存確認などを実装。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本検証を実行する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML があれば中身も検証）。
    - --strict オプションで警告を FAIL（exit code 1）として扱う。
- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。標準出力（stdout）用 StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - デフォルト保存先: logs/、ローテート 30 日分保有。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト ("INFO")。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定と CPU affinity 固定のユーティリティ。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する実装。権限不足などで失敗した場合は警告を出力してスキップ。
- ポートフォリオ構築関連（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコアが全て 0 の場合は等分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーが上限を超える場合に新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 (bull/neutral/bear)。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method (risk_based / equal / score) に応じた銘柄ごとの発注株数計算。
    - 単元（lot_size）丸め、per-position 最大、aggregate cap（available_cash） に対するスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - スケーリング後の端数処理で残余キャッシュを再配分するロジックを備える。
- 研究・分析関連
  - research/factor_research.py（設計方針およびモメンタム算出ロジックの実装を開始）
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）、ATR、出来高などを DuckDB の prices_daily / raw_financials を元に計算する設計。
    - （ファイルの末尾で実装が途中で切れているため、一部未完の可能性あり。）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツール。
    - 指標: 稼働率 (uptime_pct)、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で上書き可）。
    - 判定基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を定義。

### 変更 (Changed)
- ログ出力は stderr ではなく stdout を使用するように設計（cron / Task Scheduler で stdout/stderr の一本化を想定）。
- .env 読み込みロジックの柔軟化:
  - export PREFIX に対応、クォート付き値のエスケープ処理、インラインコメントの取り扱い（クォート無しは '#' 前にスペースがある場合のみコメント扱い）などを実装して堅牢性を向上。

### 修正 (Fixed)
- 環境変数の未設定時に早期にわかるよう、Settings._require() で ValueError を送出する仕組みを整備（起動時に必須値の欠落を明確化）。

### 注記 (Notes)
- run_monitoring は Monitoring 用 DB を環境に依存せず本番 sqlite_path を使用する挙動が意図的に組み込まれています。テスト時は注意してください。
- calc_position_sizes / apply_sector_cap 等には TODO コメントがあり、将来的に銘柄単位の lot_size 情報や価格フォールバックの拡張が予定されています。
- research/factor_research.py の実装は途中で切れている箇所が見られます（モメンタム処理の途中で終了）。本リポジトリの snapshot では未完の可能性があるため、追加実装が必要です。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールのみでの運用となります（設計上の安全挙動）。

### 互換性・移行 (Migration)
- Paper Trading を利用する場合:
  - KABUSYS_ENV を `paper_trading` に設定すると、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。本番 DB（SQLITE_PATH）とは完全に分離されます。
  - PAPER_FILL_MODE（instant/partial/never/reject）で MockBroker の約定挙動を制御します。
- 監視ループの間隔は MONITOR_POLL_INTERVAL 環境変数で調整可能（整数秒、1 未満または不正値はデフォルト 60 秒にフォールバック）。
- 起動時にログ設定を統一するため、各起動スクリプトは setup_logging(app_name=...) を呼び出してください。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートや変更履歴が別途ある場合はそちらを優先してください。