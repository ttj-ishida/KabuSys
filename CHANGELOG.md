# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて使用

----------------------------------------

## [0.1.0] - 2026-04-17

最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境変数 / 設定管理 (`kabusys.config`)
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env / .env.local 自動読み込み機能（OS環境変数を保護する仕組みを含む）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装：export 形式、クォート（シングル/ダブル、バックスラッシュエスケープ）、インラインコメント取り扱いに対応。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に：
    - J-Quants / kabu API / LINE 設定
    - DuckDB / SQLite パス、Paper Trading 用 DB パス
    - 監視関連パラメータ（PID ファイルパス、kill フラグパス、閾値等）
    - 環境（development / paper_trading / live）とログレベル検証
    - PAPER_FILL_MODE のバリデーション

- 実行・監視スクリプト
  - run_execution (`src/kabusys/run_execution.py`)
    - ExecutionEngine の起動スクリプト。
    - Paper Trading 環境時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカー生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み上げ ExecutionEngine をデーモンスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と実行 PID（data/execution.pid）管理。
    - プロセス優先度を起動直後に "high" に設定。

  - run_monitoring (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境にかかわらず本番 sqlite_path を監視用 DB として使用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）、不正値はログ警告してデフォルトにフォールバック。
    - 停止フラグ検知で終了、KeyboardInterrupt のハンドリング。
    - プロセス優先度を起動直後に "high" に設定。

- 監視 DB 初期化ユーティリティ連携
  - run_* スクリプトは監視用テーブルが存在することを保証するため `init_monitoring_db` を呼び出す（冪等）。

- Execution サブシステム（骨格）
  - ブローカーファクトリ、エンジン、注文管理、リコンシリエーション、リスク管理の組み立てロジック（run_execution での利用を想定）。
  - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit 等）を提示し、初期ポートフォリオ値を broker.get_available_cash() で取得。

- プロセス制御ユーティリティ (`kabusys.utils.process_priority`)
  - クロスプラットフォームでプロセス優先度を設定する `set_process_priority(level)` を実装（Windows/POSIX 差分吸収）。
  - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装。
  - 権限不足や未対応 OS の場合はログ警告で安全にスキップ。

- ポートフォリオ構築ライブラリ (`kabusys.portfolio`)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選択
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有時価ベース）、sell_codes を除外する機能、"unknown" セクターは上限対象外
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック
  - position_sizing:
    - calc_position_sizes: weight / equal / score / risk_based に応じた株数算出（単元株丸め、per-position 上限、aggregate cap スケールダウン、cost_buffer の考慮、残差配分ロジック）

- リサーチ / ファクター計算 (`kabusys.research`)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB を使用、データ不足時は None）
    - calc_volatility: ATR20、ATR%・20日平均出来高・出来高比率等の計算（true_range の NULL 伝播制御）
    - calc_value: PER/ROE 計算（raw_financials から target_date 以前の最新財務を取得）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンをまとめて取得（LEAD を利用）
    - calc_ic: スピアマンのランク相関（IC）計算（同順位は平均ランク処理、3件未満で None）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー
    - rank: 同順位を平均ランクにするランク関数（丸め処理で ties の検出漏れを軽減）
  - すべて DuckDB 接続を受け取り、外部ライブラリに依存しない設計。

- データ統計ユーティリティのエクスポート (`kabusys.research.__init__`)
  - zscore_normalize（kabusys.data.stats 由来）を含む主要関数群を公開。

- ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
  - raw_news テーブルのニュースを OpenAI API（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む仕組み。
  - 処理の主な仕様:
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較
    - 銘柄ごとに最大記事数／最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 1回の API 呼び出しで最大 20 銘柄をバッチ処理
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（上限あり）
    - レスポンスの厳密な JSON 検証、スコアを ±1.0 にクリップ
    - 成功分のみ ai_scores に部分的に置換（DELETE/INSERT の範囲を限定して既存スコアを保護）
  - API キー未設定時の明示的なエラーと、ルックアヘッドバイアス回避の設計注記。

- 検証ツール (`kabusys.tools.paper_verification_report`)
  - Paper Trading 用検証レポートを生成する CLI スクリプトを追加。
  - 指標および閾値（デフォルト）:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill_rate) >= 90.0%
    - 送信率 (send_rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - システム安定性、注文統計、リスク却下数、レイテンシ（avg/max/P95）等を集計・表示。
  - 日付フィルタ指定（--from / --to）と DB パス指定（--db）に対応。
  - 空データやテーブル未存在時のフェールセーフ（OperationalError を捕捉して N/A を出力）。

- パッケージ構造
  - tools パッケージの追加（__init__.py）
  - portfolio / research / ai / utils 等のモジュールを public API として __all__ を整備。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Notes / Implementation details
- 多くのモジュールは「外部接続（API や本番口座）へ直接アクセスしない」ことを設計方針としており、DuckDB / SQLite を用いたローカルデータ参照中心で実装しています。
- Paper Trading と本番 DB の分離が明確に設計されており、誤って本番 DB に書き込むリスクを低減しています。
- 設定読み込みの実装は、OS 環境変数を保護しつつ .env.local によりローカル上書きが可能になるよう配慮しています。
- 各所で権限不足やデータ不足に対するフォールバック（ログ警告・N/A 表示・スキップ）を意図的に導入しています。

----------------------------------------

今後の予定（例）
- 単体テスト追加・CI 統合
- パフォーマンス改善（DuckDB クエリ最適化・バッチ処理の検証）
- モジュール間インターフェースの安定化とドキュメント拡充

----------------------------------------

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース履歴や日付はプロジェクト方針に合わせて調整してください。）