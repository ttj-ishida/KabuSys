# Changelog

すべての重要な変更はここに記録します。本ファイルは「Keep a Changelog」方式に準拠しています。  
フォーマット: Unreleased → バージョンの履歴（新機能・変更点・修正など）。  

※ 内容はソースコードとコメントから推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションモジュールの初期実装を追加。
  - パッケージ情報:
    - kabusys.__version__ = "0.1.0"
- 実行エントリスクリプト:
  - run_execution.py
    - ExecutionEngine を起動するためのスクリプト。
    - 環境変数 KABUSYS_ENV に応じて paper_trading モード（専用 SQLite DB を使用）をサポート。
    - BrokerClientFactory を使用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を設定（高優先: set_process_priority("high")）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を参照する設計（監視は本番 DB を使う仕様）。
    - 起動時にプロセス優先度を設定（高優先）。
- 設定管理:
  - config.py
    - .env / .env.local の自動読み込み（OS 環境変数を保護する仕組み付き）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で .env を探索。
    - .env パースで引用符付き値やエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスを提供。主要設定（API トークン、DB パス、監視閾値、PID/kill flag パス、環境フラグ等）をプロパティとして取得・検証。
    - 環境変数によるフォールバック値と入力値検証（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証ロジック）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを抑止可能。
- モニタリング初期化:
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルが存在することを保証（冪等）。
- ポートフォリオ構築（純関数群）:
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限の適用（当日売却予定の銘柄を除外可能、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear, デフォルトフォールバックあり）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）に対応した発注株数計算。単元株丸め、per-stock 上限、aggregate キャップ、cost_buffer を考慮したスケーリングを実装。
- 研究・ファクター計算:
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（prices_daily を参照）。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - DuckDB 接続を受け取り SQL ベースで効率的に計算する設計。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズン対応・入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・最小サンプルチェックあり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで扱うランク変換を実装（丸め処理で ties の検出を安定化）。
  - research パッケージは kabusys.data.stats の zscore_normalize を再エクスポートしている（研究ワークフローとの連携）。
- AI / ニュース NLP:
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）に送信し、銘柄別センチメントを ai_scores テーブルへ反映する処理を実装。
    - ニュースウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC へ変換）。
    - バッチ送信（最大 20 銘柄 / API 呼び出し）、チャンクごとのエラーハンドリング、429/5xx/タイムアウトに対する指数バックオフ・リトライ。
    - レスポンスの構造検証、スコアの ±1.0 クリップ、部分失敗時の DB 保護（書き込みは対象コードに限定して置換）。
    - API キーは引数または OPENAI_API_KEY 環境変数から解決。
- ユーティリティ:
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収したプロセス優先度設定。アクセス拒否や未実装の場合はワーニングでスキップ。
    - set_cpu_affinity(cpu_count): 指定数の CPU にプロセスをピン留め（利用不可時はワーニング）。
    - psutil を利用したクロスプラットフォーム対応。
- ツール:
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプト（指定期間フィルタ可）。
    - system_status / trade_logs / risk_logs を参照して稼働率・成功率・送信率・レイテンシ（AVG/MAX/P95）などを集計し PASS/FAIL を判定する。
    - P95 計算の実装と、各指標の閾値（稼働率 99%、注文成功率 90% 等）を定義。
    - DB が存在しない場合のエラーメッセージ出力を実装。
- DB ドライバ:
  - DuckDB と sqlite3 を併用する設計。DuckDB はリサーチ用途、SQLite は監視・発注等のトランザクション用途に使用する想定。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Design decisions
- 設定関連では OS 環境変数を保護するため .env の上書き挙動を制御（.env.local は override=True）。
- 研究モジュールやポートフォリオ構築は副作用を持たない純関数設計（DB 参照は DuckDB 接続を引数で受ける等）。
- ロバスト性のため、プロセス優先度や CPU affinity の設定失敗はワーニングで済ませ、サービスの継続を優先している。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）することでテスト運用の安全性を確保。
- AI スコアリングは API 失敗時にフェイルセーフで継続し、部分成功を保護する設計。

### Security
- OpenAI API キーなど秘密情報は環境変数経由で取得する想定（config.Settings 経由での必須取得を実装）。

---

今後の更新案（例）
- モジュール間のユニットテスト追加（特に position sizing, risk adjustment, news_nlp の外部 API 振る舞い）。
- エラーハンドリングとメトリクスの強化（監視のアラート連携）。
- パラメータの設定ファイル化（現状は環境変数中心）。