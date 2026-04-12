# CHANGELOG

すべての重要な変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット: 年-月-日

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース。KabuSys プロジェクトの基本コンポーネントを実装しました。

### Added
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に基づく paper_trading モードをサポート（paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離）。
    - プロセス優先度を起動時に設定するためのユーティリティ呼び出しを組み込み（高優先度に設定）。
    - SQLite / DuckDB への接続確立とクリーンなクローズ処理を実装。
    - ExecutionEngine の起動処理（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等の組み立て）を行う。
- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - check_once() 呼び出しの例外を握り潰してログ出力し、ループ継続するフォールトトレラントな設計。
    - プロセス優先度設定と SQLite / DuckDB の初期化処理を含む。
- 設定管理
  - config.py: 環境変数 / .env ファイル読み込みを実装。  
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）により .env 自動読み込みを行う（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
    - .env パーサを独自実装（export prefix、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い、保護キーによる上書き制御）。
    - Settings クラスを追加し、各種設定値（DBパス、API トークン、監視閾値、環境モード等）をプロパティとして取得可能に。入力検証（有効な KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。
- ポートフォリオ生成ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）、等金額配分、スコア加重配分を実装。スコア全0 の場合は等配分へフォールバック。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。  
    - risk_based / equal / score の各配分方式をサポート。単元株（lot）丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer による保守的見積り、端数処理ロジック（残差に基づく追加割当て）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジームのフォールバック挙動を明記。
  - portfolio/__init__.py でこれらの API を公開。
- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB を用いたモメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）ファクター計算を実装。  
    - 各関数は prices_daily / raw_financials テーブルを使用し、対象日ベースで結果を返す（不足時は None）。
    - 大きなスキャンウィンドウやウィンドウサイズに関するコメントを含む（パフォーマンス配慮）。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリ、ランク関数を実装。外部ライブラリ不使用で標準ライブラリのみを利用。
  - research/__init__.py: 主要関数をエクスポート（zscore_normalize の re-export を含む）。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news テーブルを OpenAI API（gpt-4o-mini）でセンチメントスコアリングし ai_scores テーブルへ書き込む処理を実装。  
    - タイムウィンドウ計算（JST ベース → UTC 変換）、記事の銘柄別集約、1銘柄当たりの文字数/記事数トリム、バッチ送信（最大 20 銘柄/コール）、JSON Mode 出力期待、レスポンス検証、スコアクリッピング（±1.0）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフのリトライを実装（上限あり）。API キーは引数または環境変数 OPENAI_API_KEY から解決。
    - フェイルセーフ設計: API 失敗時はスキップして継続。部分成功時の DB 更新手法（対象コードに限定した DELETE→INSERT）で既存データ保護。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から集計して稼働率、注文成功率、送信率、P95 レイテンシ等を算出。閾値を定義し PASS/FAIL を判定。
    - コマンドライン引数 --from/--to/--db をサポート。DB 存在チェックとエラーハンドリング実装。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定を実装（Windows / POSIX 対応）。権限不足等の例外は警告してスキップする設計。
  - utils パッケージ初期化ファイル。

### Changed
- —（初回リリースのためなし）

### Fixed
- —（初回リリースのためなし）

### Notes / Implementation details
- DB:
  - SQLite は監視用（monitoring）・paper_trading 用 DB に対応。DuckDB は時系列データやファクター計算用に利用。
  - init_monitoring_db() を呼ぶ箇所は冪等に監視テーブルの存在を保証するために追加。
- ロギング:
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を設定し、重要なイベント・例外は logger を通じて記録される。
- フォールトトレラント設計が随所に盛り込まれており、外部 API エラーや一時的な DB 欠損に対して継続動作することを重視。
- 一部関数は将来的な拡張（銘柄別 lot_size の導入、価格フォールバック等）を想定した TODO コメントを含む。

---

開発・利用の際には README / PortfolioConstruction.md / StrategyModel.md 等の設計ドキュメントを参照してください（コード内コメントに参照箇所が記載されています）。