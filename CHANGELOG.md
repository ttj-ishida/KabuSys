# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記載します。  
このファイルはコードベース（src/ 配下の実装）から推測できる機能追加・設計方針・不具合回避などを元に作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし（今回スナップショットは初期リリース相当の機能群に基づき作成）

## [0.1.0] - 2026-04-18
初期リリース（コードベースの主要機能を実装）。

### 追加
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離して動作可能。
    - _STOP_FLAG（data/stop_requested.flag）検出による安全停止、実行用 PID ファイル（data/execution.pid）管理、スレッドベースのエンジン実行とグレースフルシャットダウンを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）で監視ループを終了。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する、という明示的な動作。

- 設定・環境管理
  - config.py
    - .env の自動ロード（プロジェクトルートに .git または pyproject.toml がある場合）。優先順位: OS 環境 > .env.local > .env。
    - .env 読み込みの振る舞いは override/protected（OS 環境を保護）をサポート。
    - 複数の設定プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, PAPER_FILL_MODE の検証など）を持つ Settings クラスを提供。
    - KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を実装。
    - J-Quants / kabu API 等の必須・任意項目を対話的に設定し .env を生成する機能を提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュール（pure functions）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が0の際のフォールバック（等金額）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap（当日売却予定銘柄を除外可能）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）、手数料・スリッページを見越した cost_buffer、ポジション上限（max_position_pct）、投下上限（max_utilization）や aggregate cap スケーリング、端数処理（lot 単位で丸め）を実装。
    - 価格未取得時のスキップやログ出力を含め堅牢性を確保。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで再利用できる共通ロギング設定関数 setup_logging を実装。
    - stdout への StreamHandler + 日次ローテート（TimedRotatingFileHandler）を設定し、既存ハンドラの重複を避けるため一旦クリアしてから再設定する。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - デフォルト保持日数 30 日。
  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームなプロセス優先度設定（set_process_priority）を実装。Windows / POSIX(nice) を吸収し、アクセス権限不足などは警告してスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を実装。非対応 OS / 権限不足時は警告してスキップ。

- 分析用 DB（DuckDB）統合
  - 実行・監視スクリプトともに DuckDB 接続を受け取り分析用ファイル（DUCKDB_PATH）を利用可能。各スクリプトから duckdb.connect を利用。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）から各種指標を集計しレポートを生成する CLI を提供。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 など。
    - P95 計算、日付フィルタ（--from/--to）、db パスの引数オーバーライドを実装。基準値（閾値）を定義して PASS/FAIL 判定を行う。
    - DB のテーブル欠如などに対しては安全にフォールバック（N/A / 0）してレポートを出力。

- リサーチ（ファクター計算）骨子
  - research/factor_research.py にモメンタム等のファクター算出ロジックの設計・一部実装が含まれる（DuckDB 経由で prices_daily / raw_financials を参照する想定）。（一部未完の箇所あり）

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 変更
- 環境変数パーサーの強化
  - config._parse_env_line において
    - export プレフィックスのサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しのインラインコメント処理（'#' 前にスペースがあればコメントとして扱う）を実装。
  - .env 自動ロード時に OS 環境変数を保護する protected セットを導入（意図せぬ上書きを防止）。

- validate_config の挙動
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出すように変更（導入時のデグレード耐性向上）。

- ログ出力先についての方針
  - logging_setup で stdout を使用（stderr ではない）することで cron や Task Scheduler 実行時のリダイレクト挙動を想定。

### 修正（バグ修正 / 安全改善）
- 実行・監視プロセスの優先度設定を起動直後に行い、負荷状況により安定した動作を目指す。
- run_execution / run_monitoring で DB コネクションを起動時に開き、finally ブロックで必ず閉じることでリソースリークを防止。
- run_execution は停止フラグの既存検知で起動を抑止する安全措置を追加。
- position_sizing の総投資額が available_cash を超える場合にスケールダウンして端数を lot 単位で再配分する実装（オーバーコミット防止）。

### ドキュメント／メッセージ
- 各 CLI にヘルプ / usage を追加し対話・自動実行の両方でわかりやすくした。
- バリデーション・ウィザードでのメッセージや .env 生成テンプレートに注意喚起（.env を Git にコミットしない等）を記載。

### 既知の制限（今後の改善事項）
- research/factor_research.py の一部は未完（コメントや設計方針は記載済み）。DuckDB クエリや完全実装は今後追加予定。
- position_sizing の price 欠損時のフォールバック（前日終値等）は TODO として残っている。
- 単元株（lot_size）は現状グローバル固定（将来的に銘柄別 lot_map への拡張予定）。
- config_setup の対話処理は非対話環境での自動化に未対応（CI 用には .env 管理の別途手段が必要）。

---

この CHANGELOG はソースコードから推測して作成したものであり、実際のコミット履歴とは異なります。必要があれば差分の詳細（各ファイルの導入理由、例外処理の挙動、出力フォーマット等）をさらに掘り下げて追記できます。