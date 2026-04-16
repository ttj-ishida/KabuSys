CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。

Unreleased
----------

追加予定 / 開発中のメモ（現時点では未リリース）。

- ドキュメント整備、テスト追加、内部リファクタ（想定）
- UI / 運用スクリプトの改善や、AI モジュールのロバスト化（継続作業）

[0.1.0] - 2026-04-16
--------------------

Added
- 基本パッケージ初期実装:
  - kabusys パッケージのエントリポイントとバージョンを追加（__version__ = 0.1.0）。
- 実行・監視用スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine をデーモンスレッドで起動。
    - data/stop_requested.flag を用いた外部停止フラグ検知、data/execution.pid で PID 管理。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計。
    - 停止フラグ検知・例外ハンドリング・プロセス優先度設定を行う。
- 設定管理:
  - config.Settings クラスで環境変数をラップして提供。
    - DB パス (DUCKDB_PATH / SQLITE_PATH)、paper_trading 用の PAPER_TRADING_SQLITE_PATH、PID/kill flag などをプロパティで提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV 検証（development/paper_trading/live）。
  - .env 自動ロード実装:
    - プロジェクトルートを .git または pyproject.toml で探索し、.env/.env.local を読み込み（OS 環境変数を保護）。
    - export 形式やクォート、インラインコメントの扱い、読み込み失敗時の警告等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックして候補をフィルタ（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に基づく資金乗数（bull/neutral/bear + フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注数量計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap スケーリング、cost_buffer（コスト見積り）を考慮。
    - risk_based の場合の計算式、stop_loss_pct に基づくリスクベース算出を実装。
- 研究（Research）モジュール:
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを取得）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）を計算。horizons のバリデーションを実施。
    - calc_ic / rank / factor_summary: Spearman に基づく IC 計算（ランク）、ランク付け（同位は平均ランク）、ファクター統計サマリーを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）を再エクスポート。
- AI ニュース NLP:
  - ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ、トークン肥大化対策（記事数/文字数トリム）、JSON Mode を期待した厳密なレスポンス検証、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限あり）。
    - 日付ウィンドウ（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を明確に定義し、ルックアヘッドバイアスを避ける設計。
    - API キー未設定時に明示的なエラーを返す。
- ユーティリティ:
  - utils.process_priority:
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定。権限や未サポート環境では警告を出してスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアへ固定する機能（引数チェック・例外処理あり）。

Changed
- 監視周りの挙動:
  - run_monitoring が監視用 DB を常に本番の sqlite_path に接続する仕様を明示（環境に依存しない監視を想定）。
- run_execution が paper_trading 環境の DB を分離して初期化する仕様を明確化（監視テーブルの初期化は冪等）。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを改善し、実運用での .env 設定ミスに強くした。

Security
- OpenAI API キーの扱い:
  - ai.news_nlp は API キーを引数または環境変数 OPENAI_API_KEY で受け付け、未設定の場合は ValueError を投げることで誤った運用を防止。

Notes / Implementation details
- DuckDB / SQLite の併用:
  - 実行エンジン・研究系は DuckDB（data/kabusys.duckdb）を利用し、監視や注文履歴等は SQLite を併用する設計。
- 停止制御:
  - data/stop_requested.flag を用いた外部プロセスからの停止指示、PID ファイル出力によるプロセス管理が共通パターンとして採用されている。
- Paper Trading の隔離:
  - paper_trading 環境時に mock ブローカーを利用し、本番 DB と完全分離することで検証と本番運用の安全性を担保。
- ロギング / エラーハンドリング:
  - 各所で logging を利用して情報・デバッグ・警告・例外を出力する方針。外部依存の操作（プロセス優先度設定・API 通信等）は失敗を許容して継続する設計（フェイルセーフ）。

Acknowledgements
- 主要な設計・計算ロジック（ポートフォリオ構築、ファクター計算、IC 計算、AI スコアリングなど）はドメイン仕様書（PortfolioConstruction.md, StrategyModel.md 等）に基づいて実装されています。

---
注: 本 CHANGELOG は提示されたコードベースの内容から推測して作成したものです。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の git 履歴に基づく正確な CHANGELOG を生成する支援を行います。