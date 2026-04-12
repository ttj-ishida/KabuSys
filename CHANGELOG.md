CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従っています。  

フォーマット:
- Unreleased: 開発中・未リリースの変更（必要に応じて使用）
- 各リリースはバージョンと日付を記載

Unreleased
----------
（なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基礎機能を実装。
- 実行 / エンジン関連
  - run_execution.py: 実行エントリポイント。プロセス優先度を設定し、SQLite / DuckDB に接続して ExecutionEngine を起動。
  - BrokerClientFactory によるブローカークライアント注入（実口座 / Paper Trading 切替対応）。
  - ExecutionEngine の起動に必要なコンポーネントを組み立てるための OrderRepository, OrderManager, RiskManager, Reconciler 実装を統合。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - Paper Trading モード時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視データを記録。
  - 監視開始時にプロセス優先度を上げる処理を導入（set_process_priority）。
- 設定 / 環境変数
  - config.Settings: 環境変数からの設定取得を一元化。
  - .env 自動読み込み機構（プロジェクトルートの検出: .git / pyproject.toml を基準）を実装。.env / .env.local の優先順位・保護された OS 環境変数を考慮した上書き動作をサポート。
  - 環境変数のパースを堅牢化（コメント、引用、エスケープに対応）。
  - 必須 env のチェック（_require）および各種プロパティ（duckdb/sqlite パス、PID ファイルパス、閾値等）を実装。
  - KABUSYS_ENV（development / paper_trading / live）の検証、LOG_LEVEL の検証、PAPER_FILL_MODE（instant/partial/never/reject）の検証を実装。
- ポートフォリオ構築
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等分配にフォールバック。
  - risk_adjustment: セクター集中対策（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。レジームに応じて投下資金を調整（bull/neutral/bear）。
  - position_sizing: 発注株数計算（risk_based / equal / score）、lot 単位での丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリングを実装。
- 研究（Research）モジュール
  - research.factor_research: モメンタム（1/3/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman のランク相関）計算、ファクター統計サマリー、ランク関数を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize のエクスポートを含む。
- AI / ニュース
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチでセンチメントスコアを問い合わせ、ai_scores テーブルへ書き込むロジックを実装。
    - タイムウィンドウ計算（JST 基準で前日 15:00〜当日 08:30 相当の UTC 範囲）を実装。
    - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大化対策（記事上限・文字数上限）、レスポンス検証、スコアクリッピング（±1.0）を実装。
    - API 失敗（429 / ネットワーク / 5xx）に対するリトライ（指数バックオフ）設計。
- ツール類
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して標準出力に整形して出力。
    - DB 存在チェック、期間フィルタ（--from / --to）、テーブル欠損時のフォールバック処理を備える。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定関数を実装。権限不足や未対応 OS の場合は安全にスキップして警告を出力。

Fixed / Robustness
- 環境変数パースの堅牢化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープやインラインコメント処理、クォートなしでのコメント判定などを実装。
- MONITOR_POLL_INTERVAL:
  - 不正な値（非整数・0 以下）に対して警告を出しデフォルト（60 秒）へフォールバックする安全策を導入。
- 各所での例外ハンドリング強化:
  - run_monitoring の監視ループ内で check_once() の例外をキャッチしてログに例外情報を出力し、次のポーリングへ継続。
  - paper_verification_report はテーブル欠損時に OperationalError をキャッチして指標の計算をスキップ/フォールバック。
  - process_priority の設定で権限不足や未サポート機能を捕捉し警告でフォールバック。

Documentation / Metadata
- パッケージメタ情報:
  - kabusys.__init__ に __version__ = "0.1.0" を設定。
- 各モジュールに詳細な docstring / 使用例 / 設計方針コメントを追加（特に portfolio, research, ai.news_nlp, config）。

Security
- OpenAI API キーの取り扱い:
  - ai.news_nlp は引数または環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出して安全に処理を停止する設計。

Notes / TODOs
- position_sizing の price 欠損時フォールバックや銘柄別 lot_size など拡張ポイントをコメントで記載。
- ai.news_nlp の部分は API レスポンス処理や書き込みロジックの詳細（部分成功時の置換処理など）をコメントに残し、将来的な堅牢化設計を示唆。
- DuckDB executemany に関する注意（空 params の扱い）など実運用上の注意点をコード内に注記。

Removed / Deprecated
- なし（初期リリース）

Security
- なし

---

注: 本 CHANGELOG は提示されたソースコードから推測して作成しています。機能説明やデフォルト値・環境変数名はソース内の実装に基づき要約しています。実際のリリースノートとして使用する場合は、実運用上の変更点（API 互換性・既知の問題・アップグレード手順等）を合わせて追記してください。