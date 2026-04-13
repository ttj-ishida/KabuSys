CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
シンタックスは https://keepachangelog.com/ja/ を参照してください。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開リリース。
- コア機能を追加:
  - ポートフォリオ構築モジュール（kabusys.portfolio）
    - portfolio_builder: シグナル選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）。
    - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株丸め（lot_size）、aggregate cap によるスケール調整、cost_buffer による手数料/スリッページ考慮。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - 研究（research）モジュール
    - factor_research: momentum / volatility / value の定量ファクター計算（DuckDB を利用、prices_daily / raw_financials を参照）。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）。
    - zscore_normalize を data.stats からエクスポート。
  - AI ニュース NLP（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能（バッチ処理、トークン肥大対策、スコアクリッピング、リトライ戦略、結果検証、ai_scores への書き込み想定）。
    - ニュース収集ウィンドウ計算（JST 基準 → UTC 変換）を提供。
  - 実行用エントリポイント
    - run_execution: ExecutionEngine 起動スクリプト。プロセス優先度の設定、Paper Trading 時の DB 分離（data/paper_trading.db を使用）、BrokerClientFactory を介したブローカー切替、RiskManager のデフォルト設定が含まれる。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）、監視 DB 初期化。
  - ユーティリティ
    - config: 環境変数/.env 読み込みロジック（.git / pyproject.toml を基準とするプロジェクトルート探索、.env/.env.local の優先度、export 構文・クォートやインラインコメントのパース対応、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止、必須 env チェック関数 _require）。
    - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定（set_cpu_affinity）。権限不足や未サポート環境ではログ出力して安全にスキップ。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成 CLI。期間フィルタ（--from / --to / --db）と、稼働率・注文成功率・送信率・P95 レイテンシ等の判定ロジック（閾値は定数で定義）を標準出力に出力。

Changed
- パッケージ基礎
  - パッケージメタ情報として kabusys.__version__ = "0.1.0" を設定。
- 設定とデフォルト
  - デフォルト DB/ファイルパスを明示:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
    - PID_FILE_PATH: data/execution.pid
    - KILL_FLAG_PATH: data/kill.flag
  - env 値のバリデーションを追加:
    - KABUSYS_ENV は {development, paper_trading, live} のみ許容。
    - LOG_LEVEL は標準ログレベルのみ許容。
    - PAPER_FILL_MODE は instant/partial/never/reject のみ許容。
- 実行時の安全化
  - run_monitoring と run_execution の起動時に set_process_priority("high") を行い、実行前にプロセス優先度を上げて安定化を図る（失敗時は警告ログを出して続行）。
  - 実行ループ（run_monitoring）は check_once() の例外を捕捉してログ出力の上継続するフェイルセーフ実装。
  - run_execution は paper_trading 環境では MockBroker を用い、本番 DB と完全分離して動作するよう設計。

Fixed
- 環境変数読み込みの堅牢化:
  - .env のパースロジックを改善し、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しく解釈するようにした。
  - .env.local は .env の上書きとして扱い、既存 OS 環境変数は protected として上書きを防ぐ機構を追加。

Notes / Documentation
- Paper Trading 検証ツール:
  - デフォルト閾値:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - CLI 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- リサーチ／ファクター計算は DuckDB の prices_daily/raw_financials テーブルを前提としているため、実データ投入が必要。
- ai.news_nlp の OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨のコメントと、将来的なフォールバック価格の検討メモあり。
- 一部の処理（特に ai.news_nlp の外部 API 呼び出し部分）には外部依存（OpenAI クライアント）があるため、実行環境でのキー設定やネットワーク制約に注意が必要。
- 今後の改善候補:
  - 銘柄別の lot_size 管理（現在はグローバル単位で 100 を想定）を stocks マスタ等で拡張。
  - position_sizing のより詳細な単体テストと境界ケース検証。
  - SystemMonitor / ExecutionEngine のランタイムメトリクス出力強化。

Acknowledgments
- 本リリースはコードベースから推測してまとめた CHANGELOG です。実際の変更履歴・コミットメッセージと差異がある場合があります。