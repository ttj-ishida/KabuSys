# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（src/ 以下）を読み取り、実装された機能・改善・修正点を推測してまとめたものです。

リンクやコミット参照は存在しないため、該当機能と実装ファイルを併記しています。

## [Unreleased]

- なし（初回リリースに相当する内容は 0.1.0 に含まれます）

## [0.1.0] - 2026-04-12

初回公開リリース。自動売買システム KabuSys の基本コンポーネントを実装しました。主な追加点は以下の通りです。

### Added

- 基本パッケージ初期化
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境設定 / 設定管理
  - Settings クラスにより環境変数駆動の設定管理を実装（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み機能（プロジェクトルート自動検出、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - 複雑な .env パースロジック（export 形式、クォートやエスケープ、インラインコメントの扱い）。
    - 各種設定プロパティを提供（DBパス、PID/kill フラグパス、閾値、環境判定メソッドなど）。
    - PAPER_FILL_MODE 等の入力検証（有効なモードの検査）。

- 実行 / 監視エントリポイント
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時に専用の paper trading SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組み立て。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - DuckDB 接続の初期化、および監視テーブルの冪等的初期化。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を定期実行するポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、負値や 0 はデフォルトへフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計（監視用 DB は本番 DB を参照）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコア降順、同点時の tie-breaker、スコアが全て 0 の場合のフォールバックを考慮。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap によるセクター集中制限（既存保有のセクター比率計算、sell_codes を除外）。
    - calc_regime_multiplier によるレジーム別乗数（bull/neutral/bear のマッピングと未定義レジーム時のフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes により allocation_method（risk_based / equal / score）対応の株数計算を実装。
    - lot_size（単元株）丸め、per-position/max aggregate cap、cost_buffer を用いた保守的コスト見積りとスケールダウンロジック（端数処理のための残差配分）を実装。

- 研究 / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算。
    - ウィンドウ不足時の None 処理や、SQL のウィンドウ関数を活用した効率的実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - スピアマンランク相関に基づく IC 計算 calc_ic（欠損・サンプル数不足時の安全処理）。
    - ランク関数と factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージのエクスポートに zscore_normalize を連携（src/kabusys/research/__init__.py）。

- ニュース NLP スコアリング（OpenAI 連携）
  - ai/news_nlp.py にて raw_news を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores へ書き込む機能を実装。
    - ニュース収集ウィンドウの計算（JST ベース → UTC 変換）。
    - 1銘柄あたりの記事数・文字数制限、最大バッチサイズ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ。
    - API キー未設定時は明示的にエラー（ValueError）。
    - 部分失敗に備え、対象コードのみを置換する DELETE→INSERT の更新戦略設計（部分的保護）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - CLI（--from/--to/--db）で期間フィルタして paper_trading DB から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、PASS/FAIL 判定を出力。
    - P95 計算、各種 SQL クエリ、DB 存在チェック、OperationalError に対するフォールバック処理を実装。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。

- ユーティリティ
  - process_priority と CPU affinity のユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX(Linux, Darwin, FreeBSD) の差分を吸収してプロセス優先度を設定（psutil 利用）。
    - CPU affinity を最初の N コアに固定する機能。
    - 権限不足や未サポート環境へのフォールバック処理とログ出力。

- DB / クライアント統合
  - sqlite3 / DuckDB を使った永続化と分析用 DB の分離設計（monitoring 用 sqlite / duckdb の併用）。
  - init_monitoring_db 呼び出しにより監視テーブルの冪等な初期化を実施（監視・実行双方で呼び出しあり）。

### Changed

- なし（初回リリースにおける実装内容の記載のみ）

### Fixed / Defensive improvements

- 環境変数パースと安全性
  - .env パーサの堅牢化（クォート内エスケープ、インラインコメント扱い、export プレフィックス対応）。
  - 環境変数ロード時に OS 環境変数を保護する protected オプションを採用。

- 実行時の堅牢性向上
  - run_monitoring のポーリング loop で check_once() が例外を出してもループ継続するよう例外捕捉とログ出力を追加。
  - MONITOR_POLL_INTERVAL の不正値（非整数や <= 0）に対して警告してデフォルトにフォールバック。
  - Paper 検証ツールで DB が存在しない場合のエラーメッセージを親切化。
  - psutil による優先度/affinity 設定が失敗した場合は警告ログを出して処理を継続。

### Security

- なし（API キー等の取り扱いは引数/環境変数参照で明示。機密情報は .env で管理する想定）

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートやコミット履歴とは差異がある可能性があります。必要であれば、特定機能（例: News NLP の書き込みトランザクションの挙動、ExecutionEngine のセッション終了処理等）についてより詳細な記述を追加します。