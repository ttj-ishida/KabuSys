CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
この CHANGELOG は、提供されたソースコードの実装内容から推測して作成しています（初期リリース相当のまとめ）。

Unreleased
----------
- 今後の改善候補・既知の注意点（コード内コメントより推測）
  - position_sizing.calc_position_sizes: 銘柄ごとの lot_size を個別に管理する拡張（stocks マスタの lot_size 利用）。
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を導入することでエクスポージャーの過少見積りを改善。
  - ai.news_nlp: API 呼び出し失敗時の部分更新ロールバックや冪等性の向上、chunk retry の改善。
  - DuckDB executemany の制約に関する処理をより明確にドキュメント化 / テストカバレッジを追加。

[0.1.0] - 2026-04-12
--------------------
Added
- 全体
  - 初期リリースを想定した主要コンポーネント群を追加。
  - パッケージメタ情報として kabusys.__version__ = "0.1.0" を設定。

- 設定・環境変数管理 (kabusys.config)
  - .env と .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサを実装：export 形式、クォート文字列、エスケープ、インラインコメント処理に対応。
  - OS 環境変数の保護（protected キー）を考慮した上書きロジックを実装。
  - Settings クラスで主要設定をプロパティとして提供（DBパス、API トークン、環境種別、監視閾値、PID/kill flag パスなど）。
  - 各種入力値検証を実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェック、必須 env のチェックで ValueError を送出）。

- 実行系 / エンジン (run_execution, execution/*)
  - ExecutionEngine 起動スクリプト（run_execution.py）を追加。
  - paper_trading 環境時には paper 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と完全分離する設計を導入。
  - BrokerClientFactory により環境に応じた Broker クライアント生成を想定（モックを含む）。
  - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動する起動フローを実装。
  - RiskManager の設定（RiskConfig）に初期ポートフォリオ値を broker.get_available_cash() から取得する仕組み。
  - duckdb 接続を ExecutionEngine に渡して分析や履歴参照が可能。

- 監視 / モニタリング (run_monitoring, monitoring/*)
  - SystemMonitor 用ポーリングスクリプト（run_monitoring.py）を追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックしログ出力。
  - 監視処理は環境種別にかかわらず本番 sqlite_path を利用する仕様（監視は本番 DB を参照）。

- ユーティリティ (kabusys.utils.process_priority)
  - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値を内部で切替）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
  - 権限不足や未対応環境での安全ハンドリング（警告ログを出してスキップ）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時は等配分にフォールバック。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算ロジックを実装。aggregate cap のスケーリングや lot_size による丸め、cost_buffer を考慮した保守的評価をサポート。
  - これらを __init__ でエクスポートし、純粋関数群として DB 非依存で使用可能。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research: Momentum / Volatility / Value ファクターの DuckDB ベース計算を実装（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC (Spearman rank) 計算（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティを実装。
  - DuckDB クエリはウィンドウ関数や LEAD/LAG を活用し、スキャン範囲に緩衝を持たせて週末・祝日を吸収する設計。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを生成する score_news を実装。
  - バッチサイズ、記事・文字数のトリム、JSON Mode 出力の検証、スコアの ±1.0 クリップ、再試行（指数バックオフ）など堅牢化の設計を導入。
  - OpenAI API キーの明示的な解決（引数 or 環境変数）を実装し、不足時は ValueError を送出。
  - news window 計算（JST → UTC 変換）を calc_news_window で提供。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 向け検証レポート生成スクリプトを実装。期間指定（--from/--to）や DB パス指定（--db）に対応。
  - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計し、PASS/FAIL 判定を行う基準を実装（閾値は THRESHOLD_* 定数で管理）。
  - P95 の計算、日付フィルタ組立、SQL の OperationalError 耐性（テーブル未作成時のフォールバック）を備える。

Changed
- 環境変数の自動読み込みはプロジェクトルートの検出に依存するようになり、CWD に依存しない安全な設計へ変更（配布後の動作を想定）。
- monitoring 周りは環境に依存せず常に本番 sqlite_path を参照する方針を明確化（監視データは本番 DB に記録）。
- position_sizing の aggregate cap と lot 単位の配分アルゴリズムを導入し、可用現金を超えた場合に縮小して再配分する挙動を実装。

Fixed
- .env パーサの改善により以下のケースを正しく処理：
  - export プレフィックス付き行、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント（クォートなしの場合は直前が空白/タブのときにコメントと認識）。
- calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックするロジックを追加し、ゼロ除算を回避。

Security
- OpenAI API キーは明示的に引数か環境変数 OPENAI_API_KEY で与える必要があることを明記。未設定時は実行時エラー（ValueError）で失敗するようになっている。

Notes / Known issues
- DuckDB の executemany に関する制約を回避するため、ai.news_nlp の書き込み処理は params が空でないことを事前に確認する実装を意識しているが、部分失敗時のロールバック方針は今後の改善対象。
- position_sizing の価格欠損（0.0）の場合は現状でスキップする挙動。将来的なフォールバック価格導入が想定されている（コード内 TODO）。
- process_priority / set_cpu_affinity は権限や OS によって失敗する場合があり、その場合は警告ログを出して処理を継続する設計。

ライセンス
- 本 CHANGELOG は提供コードのソースコメントおよび実装から推測して作成されています。実際のリリース履歴やバージョン付けはプロジェクトの公式リリースノートに従ってください。