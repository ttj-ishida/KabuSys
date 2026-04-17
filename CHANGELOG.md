Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットの詳細については https://keepachangelog.com/ を参照してください。

フォーマット
- バージョンは SemVer 準拠を想定しています。
- 各リリースには Added/Changed/Fixed/Deprecated/Removed/Security のカテゴリで要約を記載します。

Unreleased
---------

- なし

0.1.0 - 2026-04-17
-----------------

Added
- プロジェクト初回リリース。
- 基本アーキテクチャと以下の主要コンポーネントを実装。
  - 実行系
    - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV により paper_trading 用 DB を分離して利用（paper_trading 環境時は data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動・停止制御（停止フラグ監視・PID ファイル管理）。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
    - 監視用 DB 初期化ユーティリティ（init_monitoring_db）呼び出しの組み込み。
  - 設定管理
    - config.py: .env / .env.local の自動読み込み（OS 環境変数を保護）、プロジェクトルート探索（.git / pyproject.toml 基準）、堅牢な .env パーサ実装（export 形式、クォート／エスケープ、インラインコメント対応）。設定値取得用 Settings クラスを提供（多数のプロパティとバリデーションを備える）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - ユーティリティ
    - utils/process_priority.py: Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティ。権限不足時は警告を出して安全にスキップする。
  - ポートフォリオ構築ライブラリ（pure functions）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等分配・スコア重み（calc_equal_weights / calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）。
    - portfolio.position_sizing: 各銘柄の発注株数算出（calc_position_sizes）。risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン・再配分ロジック、手数料・スリッページ見積り用 cost_buffer 等を実装。
  - リサーチモジュール（DuckDB ベース、外部依存最小化）
    - research.factor_research: Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）。MA200, ATR20, 各種モメンタムなどを SQL で効率的に算出。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク関数・統計サマリー（factor_summary）。外部ライブラリに依存せずに Spearman ランク相関や統計量を算出。
  - AI ニュース NLP（OpenAI 経由のセンチメントスコアリング）
    - ai/news_nlp.py: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信、JSON レスポンスの検証、スコアのクリップ（±1.0）、ai_scores テーブルへの差分更新というフローの実装。バッチサイズ制限、1 銘柄あたり最大記事数・最大文字数の制限、429・タイムアウト・5xx に対する指数バックオフ再試行ロジックなどを含む。API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は例外を送出して安全に扱う。
  - コマンドラインツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシなどを計算し PASS/FAIL 判定を出力。期間フィルタ（--from/--to）、DB 指定（--db / PAPER_TRADING_SQLITE_PATH）対応。既定の閾値に基づく判定ロジックを備える。
  - パッケージ公開情報
    - __init__.py にて __version__="0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- .env 解析の堅牢化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープと閉じクォート検出、クォートなしのインラインコメント判定を実装して実運用での .env 記述差異を吸収。
- research.feature_exploration.rank: 同順位（ties）を平均ランクで扱い、丸め誤差による ties 検出漏れを回避するため round(..., 12) を用いた安定化を実装。
- position_sizing の aggregate スケーリング: cost_buffer を導入して手数料／スリッページを保守的に見積もるロジックを追加。スケールダウン時の再配分（lot_size 単位での端数処理）を安定化。
- utils/process_priority.py: 未対応 OS や権限不足時のフォールバックとログ出力を改善。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- ai/news_nlp の API キー取り扱い: OPENAI_API_KEY または明示的引数が未設定の場合は ValueError を送出して誤った匿名呼び出しを防止。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。システム側の環境変数が誤って上書きされることを防ぐ。

Notes / 実運用上の重要点
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データは本番 DB を参照する設計です。
- 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB から完全に分離されます。
- 停止制御: data/stop_requested.flag（プロジェクトルート配下）などのフラグファイルを監視して安全にプロセスを停止できる仕組みを採用しています。
- ポートフォリオ・リスク設定等のデフォルト値（例: RiskConfig, calc_position_sizes の各パラメータ）はコード内ドキュメントで明示しています。運用に合わせて環境変数や設定から調整してください。
- DuckDB を分析用途のローカル SQL エンジンとして採用。prices_daily / raw_financials / ai_scores 等のテーブルを参照してオフライン計算を行う設計です。
- 研究モジュールは外部 API や発注系には依存せず、リサーチ環境で安全に実行できるよう設計されています。

Acknowledgments
- 本リリースはシステム設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づき実装されています（コメントに参照あり）。

今後の予定（例）
- ai/news_nlp の堅牢性向上（部分失敗からの部分再試行、レスポンススキーマのさらに厳密な検証）。
- position_sizing の銘柄別 lot_size 対応（stocks マスタからの lot_map 受け取り）。
- 監視・実行のユニットテスト強化と E2E テストの追加。
- 設定周りをより柔軟にするための設定ファイルサポート（YAML/JSON）検討。