CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
  - 実行／監視ランナー
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、本番 DB と分離。
      - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による外部制御をサポート。
      - スレッドでエンジンを実行し、停止フラグ検知で安全に停止する実装。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に依らず本番 sqlite_path を使用する設計。
      - check_once() の例外はログ出力して次回ポーリングに継続するフェイルセーフ動作。
  - 設定/環境変数管理
    - config.py: Settings クラスを導入。
      - .env / .env.local 自動読み込み（プロジェクトルートの探索: .git または pyproject.toml）。
      - export KEY=val 形式、クォート値、インラインコメント等に対応した .env パーサ実装。
      - OS 環境変数を保護する protected 機構（.env.local の上書き時も保護）。
      - 各種設定プロパティのバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
      - DuckDB / SQLite のデフォルトパス、PID/kill フラグパス等を定義。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 銘柄候補選定（select_candidates）、重み計算（calc_equal_weights, calc_score_weights）。
    - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）。
      - risk_based / equal / score の割当方式をサポート。
      - 単元株丸め、max_position_pct、max_utilization、aggregate cap（スケーリング）などを実装。
      - cost_buffer を利用した保守的投資見積りをサポート。
    - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
      - セクター集中防止、unknown セクターの扱い、regime による投下資金乗数を実装。
  - リサーチ / ファクター計算
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を利用した SQL 実装）。
      - mom 1/3/6M、MA200 乖離、ATR20、20日平均売買代金、PER/ROE 取得などを実装。
      - 欠損データ時の None 扱い、ウィンドウカウント条件の実装。
    - research.feature_exploration: 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、ランク関数を実装。
      - calc_forward_returns: 任意ホライズンの将来リターンを一括取得可能。
      - calc_ic: ランク相関（スピアマン ρ）を ties 対応で計算。レコード不足時は None を返す。
      - factor_summary: count/mean/std/min/max/median を算出。
  - AI ニューススコアリング
    - ai/news_nlp.py: raw_news からニュースを集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのスコアを ai_scores に書き込む処理を実装。
      - タイムウィンドウ定義（前日15:00 JST〜当日08:30 JST を UTC で扱う）と記事トリミング（記事数・文字数上限）の実装。
      - バッチサイズ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ処理を設計内包。
      - OpenAI API キーの解決（引数または環境変数 OPENAI_API_KEY）。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティを追加。
      - Windows/Linux/macOS/FreeBSD に対応し、権限不足や未サポート環境では警告ログを出してスキップ。
  - モニタリング DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を利用して run 実行時に監視テーブルの存在を保証（冪等）。
  - ツール
    - tools.paper_verification_report.py: Paper Trading の検証レポート出力スクリプトを追加。
      - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定する閾値を実装。
      - P95 計算、日付フィルタ、DB パスの CLI 引数／環境変数解決をサポート。
  - パッケージ化
    - kabusys.__init__ にバージョン __version__ = "0.1.0" を追加。主要モジュールのエクスポートを定義。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- 設定周りで必須環境変数未設定時に ValueError を送出することで、誤った起動を防止（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。
- OpenAI API キー未設定時に明確なエラーを出す（api_key 引数または OPENAI_API_KEY 必須）。

Notes / Implementation details
- run_monitoring.py / run_execution.py は起動時にプロセス優先度を "high" に設定する呼び出しを行います（set_process_priority）。
- run_execution は paper_trading 環境向けに専用の SQLite DB（data/paper_trading.db）を使うことで、本番 DB と完全分離する設計。
- .env の自動読み込みはプロジェクトルート検出に基づき行われ、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- position_sizing の aggregate cap スケーリングや remainder を使った lot 単位の微調整など、現実的な発注数量算出に配慮した実装。

開発者向け TODO / 将来的な拡張案（コード内コメントより）
- position_sizing: 銘柄別の lot_size を導入し、stocks マスタから取得できる設計への拡張。
- risk_adjustment: price 欠損時のフォールバック（前日終値や原価）を導入してエクスポージャー見積り精度向上。
- ai/news_nlp: 処理途中での部分失敗をより堅牢に扱うためのトランザクション分割やリトライ改善。
- 監視・実行フローの統合運用監視（アラート送信、ログ集約）の強化。

--- 

注: 上記はリポジトリ内のソースコードから推測してまとめた CHANGELOG です。実際のリリース日や細かい変更履歴は開発履歴（コミットログ等）に基づき適宜更新してください。