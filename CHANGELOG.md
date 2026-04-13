CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under Semantic Versioning.

Unreleased
----------

- なし（初回リリース以降の変更はここに記載されます）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
  - 実行系 / 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を利用し、MockBrokerClient を使って本番 DB と分離して動作可能。
      - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てロジックを含む。RiskManager のデフォルト設定（max_position_pct 等）を設定。
      - 起動時にプロセス優先度を設定する仕組みを導入。
  - 監視系 / 起動スクリプト
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告ログを出す。
      - 監視用 DB 初期化（init_monitoring_db）と duckdb 接続を行いループで monitor.check_once() を定期実行。
      - 起動時にプロセス優先度を設定。
  - 設定管理
    - config.py: 環境変数 / .env ファイルの読み込み・パース機能を実装。
      - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - export 形式、クォート／エスケープ、インラインコメントの扱いなど堅牢な .env パーサを実装。
      - Settings クラスで各種設定プロパティを提供（DB パス、paper_trading パス、PID/KILL フラグ、閾値、環境判定など）。バリデーションとデフォルト値を備える。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 銘柄選定（select_candidates）、等配分（calc_equal_weights）、スコア重み配分（calc_score_weights）。
    - portfolio.position_sizing: position サイズ計算（calc_position_sizes）。risk_based / equal / score に対応し、lot_size、cost_buffer、aggregate cap のスケールダウンロジックを実装。
    - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
    - これらは DB 非依存の純粋関数として設計。
  - リサーチ / ファクター計算
    - research.factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）を DuckDB 上の prices_daily / raw_financials テーブルから計算する関数を実装。
      - 長期移動平均や ATR 等、ウィンドウベースでの計算を SQL+Python で効率的に実行する設計。
    - research.feature_exploration: 将来リターン calc_forward_returns、ランク相関（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）。
      - IC 計算はスピアマン相関（ランクの Pearson）を実装し、データ不足時に None を返す堅牢性を確保。
  - AI ニューススコアリング
    - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む機能を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく対象抽出、記事数／文字数のトリム、バッチ（最大 20 銘柄）単位での API 呼び出し、429/タイムアウト/5xx に対する指数バックオフ＋リトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する置換ロジックなどを備える。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成 CLI を追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定を行う。しきい値はソース内定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX の差異を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）設定を提供。CPU affinity 設定ユーティリティも追加。権限不足や未サポート環境では安全にフォールバックして警告を出力。
  - パッケージ初期化とエクスポート
    - 各モジュールの __init__ で主要関数をエクスポートし、kabusys.__init__ にバージョン文字列を追加。

Changed
- 実装上の設計決定（初期公開として明示）
  - 監視コンポーネントは KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データの一貫性を重視）。
  - .env 自動ロードはプロジェクトルート検出に依存し、配布後の実行でもカレントワークディレクトリに左右されないように実装。

Fixed
- 設定 / パーサの堅牢化
  - .env のパースで export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理を正しく扱えるよう改善。
- 各種計算ユーティリティの耐障害性向上
  - calc_score_weights: 全銘柄スコアが 0 の場合等金額配分にフォールバックして警告を出す。
  - factor_research / feature_exploration: データ不足・NULL 値を適切に扱い、欠損時は None を返すようにして上位呼び出し側で安全に扱えるようにした。
  - run_monitoring の MONITOR_POLL_INTERVAL バリデーションにより 0 以下や不正値で ValueError になるのを防止し、警告出力の上でデフォルトにフォールバック。

Removed
- なし

Security
- OpenAI API キーの扱いについて、api_key 引数または環境変数 OPENAI_API_KEY の明示的な指定を必須とし、未設定時は ValueError を送出して意図しない外部送信を防止。

Notes / Known limitations
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄毎の lot_size をマスタで持つ拡張を想定（TODO コメントあり）。
- 一部の価格欠損（price == 0.0）時のエクスポージャー過少見積りについて注記（risk_adjustment.apply_sector_cap に TODO）。
- DuckDB に対する executemany の制約や接続利用時の注意点はコメントで記載している（ai.news_nlp 等で考慮済み）。

Acknowledgements
- このリリースは初版のため、今後ユーザフィードバックに基づく改善・リファクタリングを予定しています。バグ報告・改善提案は issue を通じて歓迎します。