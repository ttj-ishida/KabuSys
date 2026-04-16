# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-16

### 追加
- プロジェクト初期リリースを公開。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を立ち上げるエントリポイント。KABUSYS_ENV によって paper_trading 用 DB を分離して使用可能（data/paper_trading.db がデフォルト）。停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポートし、スレッドでエンジンを実行して安全に停止できる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出、監視 DB 初期化処理を備える（監視は環境に依らず本番 sqlite_path を参照）。
- 設定/環境管理
  - config.py: Settings クラスを導入し、環境変数／.env ファイル（.env/.env.local）の自動ロードを実装。プロジェクトルートの自動検出（.git または pyproject.toml 基準）、.env のパースは export 形式、クォート、インラインコメントなどに対応。各種設定プロパティ（DB パス、PID パス、監視閾値、paper_trading 関連設定、ログレベル判定など）を提供。
  - PAPER_FILL_MODE の妥当性チェックを実装（instant/partial/never/reject）。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出ロジックを実装（risk_based / equal / score 対応）。単元株（lot）丸め、ポジション上限、aggregate cap（利用可能現金超過時のスケーリング）やコストバッファ考慮、余り分の優先割当ロジックを含む。
  - portfolio/risk_adjustment.py: セクター集中上限適用ルール（既存保有からのエクスポージャー算出と候補除外）、市場レジームに応じた資金乗数（bull/neutral/bear）を実装。未知のレジームは警告のうえフォールバック。
- 研究・特徴量モジュール
  - research/factor_research.py: Momentum（1M/3M/6M・MA200乖離）、Volatility（ATR20・相対ATR・出来高指標）、Value（PER・ROE）ファクターを DuckDB を用いた SQL ベースで実装。計算時のデータ不足に対する安全処理を含む。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ファクター統計サマリ、ランク化ユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py: 主要な研究 API をパブリックにエクスポート（zscore_normalize は data.stats から利用）。
- ニュース NLP（AI）機能（ベース実装）
  - ai/news_nlp.py: raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いたセンチメントスコア（-1.0〜1.0）生成ロジックを追加。処理はチャンク化（最大20銘柄／API呼出）、トークン肥大対策（記事数・文字数制限）、エクスポネンシャルバックオフでの再試行、レスポンス検証、スコアクリッピング、部分更新（対象コードのみを削除→挿入）などのフェイルセーフ設計を採用。タイムウィンドウ（JST 基準）の計算ユーティリティを提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を解析して稼働率、注文成功率・送信率、リスク却下数、レイテンシ（P95含む）を出力する検証レポート機能を追加。閾値判定（PASS/FAIL）を備え、日付フィルタ（--from/--to）や DB 指定（--db）に対応。P95 計算、NULL/テーブル未存在時の安全処理を含む。
- 監視 DB 初期化
  - monitoring/monitoring_db.py（参照箇所あり）を呼ぶ形で、監視テーブルの存在を起動時に保証する処理を導入（冪等）。
- プロセス優先度／CPU 固定ユーティリティ
  - utils/process_priority.py: Windows と POSIX を考慮した set_process_priority（high/normal/low）と set_cpu_affinity 実装。権限不足や未対応プラットフォーム時に警告を出して安全にスキップ。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更
- プロジェクトの設定自動ロード挙動
  - OS 環境変数を保護しつつ .env/.env.local を順に読み込む戦略を採用（.env.local は override=True で上書き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB / SQLite の共存設計
  - 実行・研究・AI 各モジュールで DuckDB および SQLite 接続を明確に使い分ける（prices_daily/raw_financials 等は DuckDB、トレードログ等は SQLite）。
- エラーハンドリング強化
  - run_monitoring/run_execution 等のメインループで例外や KeyboardInterrupt に対するログ出力とクリーンアップ処理を明示的に追加。

### 修正（バグフィックス・改善）
- .env パーサーの堅牢化
  - export 前置、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメントの扱いを正しく処理するよう改善。
- position sizing の集約上限処理改善
  - aggregate cap 超過時のスケーリングで、lot 単位の丸め・残余配分を導入し、より決定論的で再現性のある配分を実現。
- factor/feature 関数の境界条件処理
  - 欠損データや十分な履歴がない場合に None を返すなど、安全な動作を担保。
- process priority/affinity の権限エラー対策
  - psutil の AccessDenied 等発生時に警告を出して動作を継続するように変更。

### 既知の制限 / 注意点
- ai/news_nlp.py は OpenAI API キーを必須（api_key 引数または OPENAI_API_KEY 環境変数）。実行環境によっては API コストやレート制限に注意が必要。
- position_sizing 等は現在単元株数（lot_size）を全銘柄共通で扱っている（将来的に銘柄別 lot_map での拡張を想定）。
- run_monitoring は監視データを常に本番 sqlite_path に書き込む設計になっているため、テスト時は明示的にパスを変更すること。
- research モジュールは DuckDB に所定のテーブル（prices_daily, raw_financials 等）が存在することを前提とする。

### セキュリティ
- なし（このリリースで特筆すべきセキュリティ修正はありません）。

---

今後はバグ修正、ドキュメント整備、ユニットテスト追加、AI 周りの堅牢化（レート制御・コスト最適化）や銘柄別単元対応などを予定しています。