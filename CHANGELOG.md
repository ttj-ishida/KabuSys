CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/),
およびセマンティックバージョニングを想定しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ情報を追加
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み実装（プロジェクトルートの検出は .git または pyproject.toml による）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パース機能の強化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの取り扱い（スペース直前の # をコメントとみなす等）。
  - 環境変数取得ヘルパ _require を提供（未設定時は ValueError）。
  - 各種設定プロパティを追加:
    - データベースパス: duckdb_path, sqlite_path, paper_sqlite_path
    - Paper Trading: paper_fill_mode（入力値検証あり）
    - 監視関連: pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk threshold
    - ログ/環境: env, log_level, is_live/is_paper/is_dev

- 実行系起動スクリプト
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager の既定設定を定義（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）、initial_portfolio_value を broker.get_available_cash() で初期化。
    - エンジンは別スレッドで実行、data/stop_requested.flag を検知すると安全に停止。
    - PID ファイル path（data/execution.pid）を利用。

  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
    - data/stop_requested.flag による停止検知。
    - check_once() 実行中の例外はログに記録して次回ポーリングに継続。

- 監視 DB 初期化ユーティリティ
  - monitoring_db を初期化する init_monitoring_db を run スクリプトから呼び出し（冪等）。

- プロセス優先度 / CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) 実装（Windows と POSIX を抽象化）。
    - サポートレベル: "high", "normal", "low"。
    - Windows: psutil の HIGH_PRIORITY_CLASS 等を利用。
    - POSIX(Linux/Mac/FreeBSD): nice 値を使用。
    - 権限不足・未実装 API の場合は警告ログで安全にフォールバック。
  - set_cpu_affinity(cpu_count) 実装（最初の N コアにピン留め、例外時は警告してスキップ）。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告のうえ 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。lot_size 単位で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリングを実装。スケーリング時の残差配分ロジック（フラクション残差を元に追加配分）を実装。

- 研究／リサーチモジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB 上の prices_daily / raw_financials テーブル参照、営業日ウィンドウ・欠損扱いに配慮）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（任意 horizon 対応、入力検証あり）。
    - calc_ic: スピアマンランク相関による IC 計算（最小有効レコード数チェック）。
    - rank, factor_summary: ランク算出（同順位は平均ランク）と基本統計量集計（count/mean/std/min/max/median）。
  - research パッケージは zscore_normalize を外部に公開（kabusys.data.stats 依存）。

- AI ニュース NLP（部分実装） (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約し、OpenAI API (gpt-4o-mini) を用いて銘柄毎のセンチメントスコアを生成して ai_scores テーブルへ書き込む設計。
  - 設計上の特徴:
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する calc_news_window を実装。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたりのトークン制限（記事数・文字数でトリム）、レスポンス検証、±1.0 にクリップ。
    - 429/ネットワーク/5xx 等に対して指数バックオフでのリトライ（上限 _MAX_RETRIES）。
    - API キーの解決ロジック（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - 注意: ファイル末尾が途中で切れている（_fetch_articles の呼び出し後の実装が途中）。現在は設計仕様と前半ロジックが用意されているが、完全実装・DB 書込の統合は未完。

- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - CLI ツールを追加: 指定期間の paper_trading DB（デフォルト data/paper_trading.db）を読み、以下を出力:
    - システム安定性（稼働率、総ポーリング数、エラー数）
    - 注文指標（Created/Filled/Sent 件数、成功率・送信率）
    - リスク却下数（risk_logs）
    - API レイテンシ（avg / max / P95）
    - PASS/FAIL 判定（閾値はソース内で定義: 稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）
  - P95 は独自関数で算出。SQL の欠損/テーブル未存在時のフォールバックを実装。
  - CLI オプション: --from, --to, --db。

Changed
- DB 周り
  - DuckDB と SQLite を併用する設計に統一（Execution/Monitoring/Research 各所で接続を受け渡し）。
  - monitoring 初期化を起動時に保証（init_monitoring_db の呼び出しを追加し冪等化）。

- エラーハンドリング/安全性
  - 起動時にプロセス優先度設定を試行し、失敗時は警告ログで継続する堅牢化。
  - 長時間処理・外部 API 呼び出しでのエラーはログに残して処理継続する方針（監視ループ、AI リクエスト等）。
  - Paper Trading と本番 DB を明確に分離（paper_sqlite_path の導入、Execution 起動ロジックで切替）。

Fixed
- CLI / ツールの安定化
  - paper_verification_report の日付フィルタリングを ISO8601 UTC 文字列で扱うようにし、日付境界を明確化。
  - レポート生成時にテーブルが存在しない場合でもエラーにならないように各クエリを try/except で保護。

Known issues / Notes
- src/kabusys/ai/news_nlp.py の実装が途中で切れている（ファイル末尾が不完全）。score_news の記事取得/バッチ送信以降の実装と、ai_scores への安全な置換ロジックは未完のため、現状ではそのまま実行すると例外または動作しない可能性があります。
- position_sizing の価格欠損時の扱いについて注釈あり（TODO: 前日終値や取得原価でのフォールバックを検討）。
- process_priority の設定は権限やプラットフォームに依存するため、環境によっては効果がない場合がある（その場合は警告ログのみ）。

Security
- なし

Acknowledgments / Notes
- DuckDB を解析用 DB として利用することで、リサーチ処理を本番注文系から切り離している点に注意。
- Paper Trading 用の DB を別ファイルで保持する方針により、検証時の誤操作による本番データ汚染リスクを低減。

--- 

（今後のリリースでは AI モジュールの完成、テストカバレッジの追加、ドキュメント整備、API キー・シークレット管理の改善などを予定しています。）