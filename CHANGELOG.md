# Changelog

すべての重要な変更は Keep a Changelog 準拠で記録します。  
各リリースは Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで整理しています。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-16

初期リリース。日本株自動売買システム「KabuSys」の基盤機能をまとめて追加しました。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールのエクスポート整備（portfolio / research / tools 等）。

- 実行/監視起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番DBと完全分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンは別スレッドで実行し、data/stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - PID ファイル（data/execution.pid）を扱う仕組みを備える。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう明確化。
    - stop flag による停止、例外発生時のログ出力とループ継続処理を実装。
    - DuckDB 接続（duckdb）を用いた処理準備を行う。

- 設定管理
  - kabusys.config.Settings クラスを追加。
    - .env / .env.local の自動ロード機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑制。
    - .env 解析の堅牢化（export プレフィックス対応、シングル/ダブルクォートとエスケープ対応、インラインコメントの取り扱い）。
    - 必須環境変数チェック（_require）で未設定時に ValueError を送出。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / PID・kill flag / モニタ閾値 / 環境判定 等）。
    - env 値・LOG_LEVEL・PAPER_FILL_MODE 等の妥当性チェックを実装（不正値で明示的なエラー）。
    - settings = Settings() の単一インスタンスをエクスポート。

- 監視関連
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等）。
  - SystemMonitor の呼び出し箇所（run_monitoring/run_execution）を実装。

- 実行エンジン周辺コンポーネント（インターフェース）
  - OrderRepository / OrderManager / ExecutionEngine / Reconciler / RiskManager 等の組み立てを行う起動フローを追加（run_execution での接続点を整備）。
  - RiskConfig のデフォルト値と初期ポートフォリオ評価を Execution 側で設定。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分／スコア加重配分（スコア全0時のフォールバック警告を実装）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限ロジック（売却予定銘柄の除外や "unknown" セクター扱いの挙動を含む）。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear をマップ、未知レジームは 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケールダウン）や cost_buffer を考慮した保守的算出。
    - スケールダウン時に端数を lot 単位で再配分するアルゴリズムを実装。

- 研究（research）モジュール
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200乖離の計算（DuckDB を使用）。
    - calc_volatility: ATR20・相対ATR・平均売買代金・出来高比率の計算。
    - calc_value: PER / ROE の計算（raw_financials と prices_daily を結合、最新財務レコードを選択）。
    - 入力データ不足時の None ハンドリングやウィンドウ制限を実装。
  - feature_exploration
    - calc_forward_returns: 将来リターン（指定ホライズン）の一括取得（動的 SQL 生成、ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（有効レコード 3 未満は None）。
    - rank / factor_summary: ランク化（同順位は平均ランク）とカラム統計量（count/mean/std/min/max/median）算出ユーティリティ。
  - research パッケージは data.stats.zscore_normalize を再エクスポート。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
  - 主要機能:
    - ターゲット日の「前日15:00 JST ～ 当日08:30 JST」に相当する UTC ウィンドウ計算（calc_news_window）。
    - raw_news / news_symbols を銘柄ごとに集約、最大記事数・文字数でトリムする保護（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄／バッチで API 呼び出し、429/ネットワークエラー/5xx に対し指数バックオフでリトライ。
    - レスポンス検証、スコアを ±1.0 にクリップ、部分成功時に該当銘柄だけを置換する戦略（DELETE+INSERT の限定実行）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決、未設定時は ValueError を送出。
    - フェイルセーフ設計：API 失敗時はスキップして処理継続。
  - DuckDB executemany に関する注意（コメント）を含む実装メモ。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプト（コマンドライン実行可能）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算・表示。
    - DB が存在しない場合のエラーメッセージ、テーブル未存在時の耐性（sqlite3.OperationalError を捕捉してデフォルト値を使用）。
    - P95 計算、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count): 指定コア数にピン留めする機能（None で未設定、1 未満は ValueError）。
    - 権限不足や未対応 OS 時に警告を出し処理継続する堅牢さを実装。
  - その他モジュール __init__ ファイルの追加/整理。

### Changed
- （初期リリースのため該当なし）

### Fixed
- 各種計算関数での欠損値・ゼロ除算に対する安全処理を追加（例: calc_value の EPS=0 対応、factor_summary の None 除外、calc_forward_returns の horizons バリデーション）。
- paper_verification_report でテーブル未存在時にもレポート生成が継続するよう try/except を導入。

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数または環境変数に限定し、未設定時は明示的にエラーとすることで誤動作を防止。

---

注記:
- 実装は外部ファイル（DB スキーマ、ExecutionEngine 実装、SystemMonitor 本体、Broker 実装など）に依存しており、ここに記載したのは公開されたコードから推測できる動作・設計の要点です。
- 将来的なリリースでは、各コンポーネント（ExecutionEngine、SystemMonitor、AI 統合等）についてより詳細な変更ログを分割して記載します。