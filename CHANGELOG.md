# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
バージョン番号はパッケージの __version__ に合わせています。

## [Unreleased]

（現時点では未リリースの差分はありません）

---

## [0.1.0] - 2026-04-17

初回リリース。KabuSys の基本機能を実装しました。主な追加点は以下のとおりです。

### 追加
- 基本パッケージ
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 設定管理
  - 環境変数および .env/.env.local の自動読み込み機能を実装（src/kabusys/config.py）。  
    - プロジェクトルートを .git または pyproject.toml から検出して .env を探索。  
    - export 付き行・クォート・エスケープ・インラインコメント等に対応した独自パーサを実装。  
    - OS 環境変数を保護しつつ .env.local で上書き可能。  
    - 必須変数チェック（_require）や各種設定プロパティ（DBパス、Paper Trading 関連、監視閾値、環境種別判定など）を提供。  
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。

- 実行用スクリプト
  - Execution Engine 起動スクリプトを追加（src/kabusys/run_execution.py）。  
    - KABUSYS_ENV が paper_trading の場合は paper 用 SQLite を使用（data/paper_trading.db をデフォルト）。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。  
    - 停止フラグ（data/stop_requested.flag）と PID ファイルを利用した安全停止処理を実装。  
    - データベース初期化（監視テーブルの冪等初期化）と DuckDB 接続を行う。

  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。  
    - Monitoring は常に本番の sqlite_path を使用する設計。  
    - 停止フラグの検知、例外時のログ出力、プロセス優先度設定を組み込み。

- 監視関連ユーティリティ
  - 監視用 DB 初期化（init_monitoring_db を参照して使用箇所で呼び出し）を組み込み（各起動スクリプトで使用）。

- プロセス優先度 / CPU affinity
  - クロスプラットフォームでプロセス優先度を設定するユーティリティを実装（src/kabusys/utils/process_priority.py）。  
    - Windows / POSIX（Linux, macOS, FreeBSD）対応。失敗時は警告を出してスキップ。  
    - CPU affinity を最初 N コアに固定する機能を実装。

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio_builder: シグナル選定（スコア降順）と等金額／スコア加重の重み計算（src/kabusys/portfolio/portfolio_builder.py）。  
    - スコアが全て 0 の場合は等金額にフォールバックして警告を出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。  
    - 「unknown」セクターは上限適用をしない等の仕様を明示。  
    - レジーム乗数は bull/neutral/bear をサポートし、未知レジームはフォールバック。
  - position_sizing: 発注株数算出ロジックを実装（risk_based / equal / score）（src/kabusys/portfolio/position_sizing.py）。  
    - lot_size（単元）丸め、1銘柄上限・集約キャップ（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残余配分の端数処理を実装。

- リサーチ / ファクター計算
  - factor_research: モメンタム（1/3/6M、MA200乖離）、ボラティリティ（ATR20、平均売買代金等）、バリュー（PER/ROE）を DuckDB 上で計算する関数を追加（src/kabusys/research/factor_research.py）。  
    - ウィンドウ / 欠損データへの耐性を備え、SQL で効率的に取得する実装。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計要約、ランク付けユーティリティを追加（src/kabusys/research/feature_exploration.py）。  
    - 外部依存（pandas 等）を用いず標準ライブラリと DuckDB で実装。

- AI ニュース NLP（OpenAI 統合）
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に格納する処理の骨格を実装（src/kabusys/ai/news_nlp.py）。  
    - タイムウィンドウ計算、記事集約（記事数・文字数トリム）、バッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時のデータ置換戦略（部分的 DELETE→INSERT）など設計方針を文書化。  
    - OpenAI API キー未設定時に ValueError を送出。  
    - （注）ファイル末尾で処理が途中で切れており、_fetch_articles 等の実装は別ファイルや今後の追加を想定。

- ツール
  - paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。  
    - 稼働率・注文成功率・送信率・P95レイテンシ等を集計し PASS/FAIL 判定を行う。  
    - CLI 引数 --from/--to/--db に対応し、デフォルト DB は data/paper_trading.db。  
    - 各種閾値（稼働率 99% 等）を定義。欠損テーブルに対する耐性も実装。

- パッケージエクスポート
  - research / portfolio モジュールの公開 API を __init__.py で整理してエクスポート。

### 変更
- ログ・エラーメッセージを日本語で記述し、運用者向けの情報を追加（起動環境ログ、停止フラグ検知ログ、各種警告ログなど）。
- DB 接続の取り扱いを統一（起動スクリプトで明示的に close する等）。

### 修正（バグ修正・回避策）
- 環境変数の不正値に対して安全にフォールバックする実装を追加：
  - MONITOR_POLL_INTERVAL が 0 以下や非数の場合はデフォルト（60 秒）にフォールバックして警告を出力（src/kabusys/run_monitoring.py）。  
  - PAPER_FILL_MODE の不正値は ValueError を発生させて早期発見（src/kabusys/config.py）。
- psutil による優先度設定や CPU affinity の実行時に発生しうる AccessDenied / NotImplementedError 等を捕捉し、警告ログを出して処理を継続するようにした（src/kabusys/utils/process_priority.py）。
- DuckDB executemany に関する注意（空パラメータ回避）を実装方針として明記（news_nlp 設計コメント）。

### ドキュメント（コード内コメント）
- PortfolioConstruction.md / StrategyModel.md 等外部ドキュメント参照を多く含め、アルゴリズム根拠・将来拡張ポイント（lot_size 銘柄別対応、価格フォールバックなど）をコメントに残しています。
- news_nlp, research などで設計方針（ルックアヘッドバイアス防止、外部 API への安全対策等）を明示。

### 既知の制限 / 今後の作業予定
- news_nlp の記事取得・バッチ送信周りで未完の内部関数（例: _fetch_articles の続き）が存在しており、完全なエンドツーエンド処理は次リリースで実装予定。  
- 一部の TODO（銘柄毎の lot_size を stocks マスタに持たせる等）を残しています。  
- DuckDB のバージョンや executemany の挙動に依存する箇所があるため、実運用前にデータベース周りの検証を推奨します。

---

このリリースは初期実装をまとめたもので、運用・テストを通じて順次改善を行っていく予定です。ドキュメントや API 安定化、テストカバレッジの拡充を今後の優先課題としています。