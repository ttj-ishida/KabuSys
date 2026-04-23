# CHANGELOG

すべての変更は "Keep a Changelog" 形式に従い、セマンティックバージョニングを使用します。  
過去リリースや機能の追加点・注意点を日本語でまとめています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

## [Unreleased]
（次のリリースに向けた変更はここに記載）

---

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションパッケージを初期実装として追加。
  - パッケージバージョン: kabusys.__version__ = "0.1.0"

- 実行用スクリプト / デーモン類
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - スレッドでエンジンを起動し、data/stop_requested.flag による外部停止をサポート。実行 PID を data/execution.pid に保持。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み（utils.process_priority）。

  - run_monitoring.py
    - システム監視ループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視データを一元化。
    - data/stop_requested.flag による停止、KeyboardInterrupt のハンドリング、SQLite / DuckDB 接続のクリーンなクローズを実装。

- 設定管理とウィザード
  - config.py
    - Settings クラスを実装。環境変数の取得・検証（KABUSYS_ENV, LOG_LEVEL 等）を提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を OS 環境変数にマージ。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサはクォート、エスケープ、inline コメント等に対応。
    - Paper Trading 関連の設定: PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH サポート。

  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを追加。既存 .env の読み込みとマスク表示、確認後にファイル出力。
    - 標準的な設定項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、KILL_FLAG_CLEAR_ON_START など）をサポート。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML がある場合）を実装。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築ライブラリ（pure function）
  - portfolio.portfolio_builder
    - select_candidates: 信号をスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア重み配分（スコア合計が0のとき等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存ポジションを考慮し、上限超過セクターの候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数（未定義はフォールバック1.0）。bear の説明と注意書きあり。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based, equal, score）に対応した株数計算。
    - 単元株（lot_size）、max_position_pct、max_utilization、コストバッファ等を考慮した aggregate cap のスケーリングロジックを実装。スケーリング後の端数配分を残差順で行うロジックあり。

- ユーティリティ
  - utils.logging_setup
    - 共通のログ設定ユーティリティを導入。コンソール出力（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ登録。
    - LOG_DIR の自動作成（失敗時はファイルハンドラをスキップしてコンソールのみ継続）。LOG_LEVEL の解決順を明示。
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice を吸収）。CPU affinity を最初 N コアに固定する関数も提供。
    - アクセス権限不足時は警告を出してスキップ。

- 監視・計測関連
  - monitoring.monitoring_db (参照される初期化関数を run_* で呼び出し、監視テーブル存在を保証)
  - monitoring.system_monitor (run_monitoring から使用される SystemMonitor の起動/チェックロジックを想定)

- ツール
  - tools.paper_verification_report.py
    - ペーパートレード DB を解析して検証レポートを生成するスクリプトを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等を計算し、定義済み閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）に基づいて PASS/FAIL を判定。
    - 日付フィルタ --from/--to、--db オプションをサポート。P95 計算、欠損データの扱い（N/A）に対応。

- 研究用
  - research.factor_research (途中まで実装)
    - DuckDB を使ったモメンタム / ボラティリティ / バリュー等のファクター計算を想定するモジュールの骨組み。calc_momentum の実装が開始されている（ファイル末尾で途中）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Usage highlights
- 環境変数自動読み込み:
  - プロジェクトルートが検出される場合は .env を自動で読み込みます。テスト等で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と Live の DB 分離:
  - run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を使用するため、本番 SQLite とログを分離できます（PAPER_TRADING_SQLITE_PATH にて上書き可能）。
- ログ出力:
  - ファイル出力先はデフォルト logs/。ファイル出力に失敗してもコンソール出力は継続されます。
- 停止フラグ:
  - data/stop_requested.flag を置くことで監視ループや実行エンジンを外部から優雅に停止できます。
- 実行優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出します。権限がない環境では警告が出てスキップされます。

### Known limitations / TODO
- research.factor_research の実装は未完（calc_momentum の先頭で途切れ）。
- position_sizing: lot_size の将来的な銘柄別対応（stocks マスタに lot_size を持たせる）を予定。
- apply_sector_cap: price_map の欠損（0.0）を補完する拡張（前日終値や取得原価フォールバック）を検討中。
- 一部モジュール（monitoring.system_monitor、execution.Engine 等）はこの差分において外部ファイルとして参照されており、完全な動作はそれらの実装に依存します。

---

その他、細かなログメッセージや検証メッセージは各モジュール内コメントおよび docstring に記載しています。リリースノートに不足があれば差分や追加の要望をお知らせください。