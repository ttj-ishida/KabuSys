# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
通常の運用では、重要な変更はリリースごとにここを更新してください。

全般ルール:
- 重要な新機能は「Added」
- 既存機能の振る舞い変更は「Changed」
- 不具合修正は「Fixed」
- 削除や非推奨はそれぞれ「Removed」「Deprecated」に記載

---

## [Unreleased]

### Changed
- .env パーサーの挙動を詳細化・堅牢化
  - export KEY=val 形式やシングル/ダブルクォート内でのバックスラッシュエスケープに対応。
  - クォートなしの場合のインラインコメント扱いを改善（`#` の直前が空白/タブのときのみコメントとみなす）。
  - .env の読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行うため、CWD に依存しない。
  - OS 環境変数を保護するための上書き制御（protected キーセット）を導入。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0以下や非整数）を検出してデフォルトにフォールバックするように改善（監視ループのクラッシュ回避）。
- ロギング関連でログディレクトリ作成失敗時にファイル出力を無効化してコンソール出力のみで継続するフォールバックを追加。

---

## [0.1.0] - 2026-04-21

初回公開リリース。主要コンポーネントを実装しました。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き機能（デフォルト 60 秒）。
    - 停止はプロジェクト内の `data/stop_requested.flag` を検知して安全に終了。
    - Monitoring は KABUSYS_ENV に依らず本番用 SQLite（`SQLITE_PATH`）を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録して本番 DB と分離。
    - 実行中の PID の管理と `data/stop_requested.flag` による外部停止対応を実装。
    - ExecutionEngine は別スレッドで実行され、メインスレッドは停止フラグを監視。

- 設定・環境管理
  - config.py
    - Settings クラスでアプリケーション設定を環境変数から取得。
    - 各種デフォルトパス（DuckDB/SQLite 等）、閾値（CPU/MEM/DISK）やログ設定、Paper Trading 関連設定を提供。
    - `PAPER_FILL_MODE` の妥当性チェック実装（"instant"|"partial"|"never"|"reject"）。
    - 環境自動ロード機能（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を実装。
    - 各種設定項目（KABUSYS_ENV や API トークン、DB パス、ログレベル等）を対話的に入力可能。
    - .env の書式テンプレート化と保存機能、シークレット項目のマスク表示を提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を実装。
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイル存在/パース検証（PyYAML 任意）、
      および本番（live）時の追加ガード（LINE 通知設定や Kill Switch の自動クリア設定の注意喚起）を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定する共通ユーティリティを実装。
    - ログレベル・ログディレクトリ解決ルール、既存ハンドラのクリア処理、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してカレントプロセスの優先度（high/normal/low）を設定。
    - CPU affinity 設定用ヘルパーを実装（利用コア数の上限チェック、権限不足時の警告）。
    - 権限不足や未対応 OS では安全にスキップしてログに警告を出す設計。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのランキング・候補選定（スコア順、タイブレークは signal_rank）と等金額／スコア加重の重み計算を実装。
    - スコア合計が 0 の場合のフォールバック（等金額）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（既存ポジションを考慮して同一セクターの新規候補を除外）を実装。unknown セクターは制限対象外。
    - レジーム（bull/neutral/bear）に応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算（allocation_method: risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・利用可能現金による aggregate cap 調整（スケールダウンと余剰キャッシュの端数配分）を実装。
    - open_prices の欠損時のスキップやログ出力を実装。

- Research / ファクター計算
  - research/factor_research.py
    - DuckDB を用いて定量ファクター（Momentum, Value, Volatility, Liquidity 等）を計算するモジュールを追加。
    - 設計方針として prices_daily / raw_financials のみ参照し、外部 API に依存しない純粋関数群を想定。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite ログ（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計してレポート出力する CLI を実装。
    - P95 計算ユーティリティ、期間フィルタ、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を実装し、PASS/FAIL 判定を行う。

- Monitoring DB 初期化
  - monitoring/monitoring_db モジュール経由で起動時に監視用テーブルの存在を保証する初期化処理を追加（init_monitoring_db を使用）。

### Changed
- run_monitoring / run_execution 起動時に最初にプロセス優先度を "high" に設定するようにして、監視／実行の応答性を高める設計とした。

### Fixed
- ExecutionEngine 起動時、paper_trading 環境では paper 用 SQLite を確実に使用して本番 DB とのデータ分離を実現。
- run_execution のスレッド監視ループで停止フラグ検知時に安全に engine.stop() を呼ぶ処理を追加。
- .env 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入（テスト用途）。

### Security
- config_setup.py で生成する .env ファイルに対し「絶対に Git にコミットしないこと」を明記。
- シークレット項目はウィザード表示時にマスクして表示。

---

### Internal / Notes
- 一部モジュール（例: research/factor_research.py）は将来的に更なるテストや最適化が想定されています（関数分割、DuckDB クエリの最適化等）。
- ロギングやプロセス優先度の設定は実行環境の権限に依存するため、権限不足時は警告ログを出すのみでフェイルしない設計です。
- Paper Trading の挙動（MockBroker の fill_mode 等）は環境変数で調整可能です。PAPER_FILL_MODE の無効値は起動時に例外を発するため設定に注意してください。

---

これ以降のリリースでは、主に以下を予定しています（未実装/改善案）:
- Strategy モジュールの具体的なシグナル生成ロジックの完成とテスト
- Helm / systemd の起動スクリプト用の起動例およびデプロイ手順の追加
- DuckDB / SQLite のマイグレーション・スキーマ管理ツール
- 単体テスト・CI の整備（特にファイナンス計算の回帰テスト）

---

参考:
- 実行例:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

（この CHANGELOG は、提供されたコードベースの内容から推測して作成しています。実際のコミット履歴に基づくものではありません。）