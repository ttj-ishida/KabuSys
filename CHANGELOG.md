# Changelog

すべての重要な変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、このログはコードベースの内容から推測して作成しています（自動生成ではなく手作業による推定記述です）。

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 実行系・監視系のエントリポイントを追加
  - run_execution.py
    - ExecutionEngine をスレッドで起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御用の stop flag（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）を使用。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てを行う。
    - RiskManager の初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込んだ初期化処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する実装を採用。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ検知時に安全にループを終了。

- 設定・環境変数管理（config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local の自動読み込みを実装。
  - .env パーサ実装（クォート、エスケープ、行コメント、`export KEY=val` 形式に対応）。
  - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - OS 環境変数を保護するため `.env` の上書きロジックで保護セット（protected keys）を使用。
  - Settings クラスを導入し、アプリケーションで使う設定値（DB パス、API トークン、監視閾値、環境種別など）をプロパティとして提供。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を追加。
  - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

- ポートフォリオ構築・ポジションサイズ計算（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: スコア降順＋タイブレーク（signal_rank）による候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア正規化配分を提供。スコア合計が 0 の場合は等分にフォールバックして WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap: 同一セクター集中を抑えるための候補フィルタ。既存ポジションからセクター別エクスポージャーを算出して閾値超過セクターの候補を除外。unknown セクターは上限適用の対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックして WARNING を出力。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方法に対応した株数算出。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積り、端数再配分アルゴリズムを実装。

- 研究用モジュール（kabusys.research）
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB を用いた各種ファクター計算を実装（MA200、ATR20、各種リターン、PER/ROE等）。データ不足時は None を返す保守的な設計。
    - DuckDB のウィンドウ関数を活用した効率的なクエリ構成。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21）の将来リターンを一括取得する汎用実装。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足や同順位処理に配慮。
    - rank / factor_summary: ランク付け・要約統計量のユーティリティを標準ライブラリだけで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）とも連携できるようエクスポートを整備。

- ユーティリティ（kabusys.utils）
  - process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。権限不足や未対応 OS でのフォールバックを考慮して警告を出す。
    - set_cpu_affinity(cpu_count): 指定コア数に固定するユーティリティを追加（None で無効化）。例外時は警告でスキップ。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 検証用レポートを生成する CLI を実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数を算出して PASS/FAIL 判定を出力する。
    - P95 計算、期間フィルタ、DB 存在チェック、各テーブル存在しない場合のフォールバック処理を実装。
  - packages/modules の __init__ に必要なエクスポートを整備。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込むための実装（news window 計算、バッチサイズ、トークン肥大化対策、スコアクリップ、リトライ方針など）。
  - API キー解決、時間ウィンドウ（JST→UTC 変換）ロジックを実装。

- パッケージ基礎情報
  - __init__.py によるバージョン（0.1.0）および主要サブパッケージの __all__ 定義を追加。

### Changed
- .env ファイルの読み込み順序・上書きルールを明確化
  - 読み込み優先順位: OS 環境 > .env.local > .env
  - .env.local は OS 環境を保護しつつ上書き（override=True）されるように実装。
- DB 初期化の冪等化
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証する（既に存在する場合でも問題とならない）。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL の不正値に対してデフォルトへフォールバックする警告ログ追加。
  - 監視ループは停止フラグを監視し、安全に DB 接続をクローズして終了するように調整。
- run_execution の挙動
  - stop flag が既に立っている場合は起動を中止するガードを追加。
  - エンジン停止時は engine.stop() を呼び出し、join を待つ実装により安全にシャットダウンする。
- position_sizing のスケーリング／端数処理アルゴリズムを改善
  - lot_size 単位での丸め、残余キャッシュを用いた端数再配分ロジックを導入し、投下合計が available_cash を超えた場合に安定的にスケールダウン。
- factor / research 実装のパフォーマンス考慮
  - DuckDB のウィンドウ関数／単一クエリでの複数ホライズン同時算出などにより I/O を抑制。

### Fixed
- 環境変数パースの不具合修正（推定）
  - .env のクォート処理やエスケープ処理、インラインコメントの扱いを改善し、誤ったパースによる設定ミスを防止。
- process_priority のエラー耐性強化
  - 権限不足や未対応プラットフォームでの例外をキャッチしてログ警告でスキップするように修正。
- paper_verification_report の統計処理堅牢化
  - テーブルが存在しない／データ不足のケースを sqlite3.OperationalError で捕捉し、レポートを N/A や 0 件で表示するフォールバックを追加。
- research.rank の同順位処理での丸めを導入
  - 浮動小数丸め（round(v,12)）により ties の誤検出を防止。

### Deprecated
- なし（初回リリースのため該当なし）

### Removed
- なし（初回リリースのため該当なし）

### Security
- 設定周りで OS 環境変数の上書きを防ぐ保護機構を実装（.env の読み込み時に OS 環境を protected keys として扱う）。

---

注記:
- ai/news_nlp.py は OpenAI との連携や詳細なレスポンス検証・DB 書き込み処理を含む実装が存在しますが、提供されたコードは途中で切れている箇所があるため、細部（DB への upsert ロジックやエラーハンドリングの完全な実装）は内部実装に依存します。
- 実際のリリースノート作成時はコミット履歴や PR/issue を参照して変更点を確定してください。本 CHANGELOG はコード内容からの推測に基づく草案です。