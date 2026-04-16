CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット
-----------
- 変更はカテゴリごとに分類（Added, Changed, Fixed, etc.）。
- バージョンはリリース日を付記します。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------

Added
- 基本パッケージ構成の初回実装（kabusys 0.1.0）。
  - パッケージ情報: __version__ = "0.1.0"。

- 実行系 / プロセス起動スクリプト
  - run_execution.py を追加：
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler など依存コンポーネントを組み立て。
    - エンジン用 PID ファイルの取り扱い（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を実装。

  - run_monitoring.py を追加：
    - SystemMonitor を用いたポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトへフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは production DB を想定）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続の確実なクローズ。

- 設定管理
  - config.py を追加：
    - .env 自動読み込み機構（プロジェクトルートは .git または pyproject.toml を探索して検出）。
    - .env の行パーサーは export プレフィックス、クォート・エスケープ、インラインコメント対応等を実装して堅牢化。
    - .env 読み込み時に OS 環境変数を保護する protected 機能を導入（.env.local は override=True）。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視 / システム設定等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject）。
    - paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start、閾値設定（CPU/MEM/DISK）などを提供。
    - KABUSYS_ENV の検証（development, paper_trading, live）。

- 監視用 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア降順・タイブレーク処理）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア比率配分、全スコア0なら等配分にフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限。既存保有・売却予定を考慮し "unknown" セクターを除外しない設計）
    - calc_regime_multiplier（レジームに応じた資金乗数: bull/neutral/bear）
  - portfolio/position_sizing.py:
    - calc_position_sizes（risk_based / equal / score の配分方式、lot_size 切り捨て、aggregate cap によるスケーリング、コストバッファ考慮）
    - 投資上限・利用上限・手数料/スリッページ推定を反映した安全な株数決定ロジック

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum（1M/3M/6M リターン、MA200乖離）
    - calc_volatility（ATR20、相対ATR、20日平均売買代金、出来高比）
    - calc_value（PER, ROE を raw_financials と prices_daily から算出）
    - DuckDB を用いた SQL ベースの実装、計算時のデータ不足ハンドリング（None を返す）
  - research/feature_exploration.py:
    - calc_forward_returns（将来リターンの集計、任意ホライズン対応、入力検証）
    - calc_ic（スピアマンランク相関による IC 計算、3 銘柄未満で None）
    - rank（同順位は平均ランクで処理）
    - factor_summary（count/mean/std/min/max/median）

- ニュース NLP（AI スコアリング）
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別 ai_score を ai_scores テーブルへ登録する処理を実装。
    - バッチサイズ, 最大記事数/文字数トリム、JSON モード出力を前提としたプロンプト設計。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）。
    - ニュース集計ウィンドウは JST 基準で定義（前日15:00〜当日08:30、内部では UTC に変換）。
    - OpenAI API キーの引数/環境変数解決。

- ツール類
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値と照合して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、--db オプションや環境変数で上書き可能。
    - 欠損テーブルを考慮したフォールバック（OperationalError 発生時は N/A / 0 で扱う）。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）。
    - set_cpu_affinity 実装（最初の N コアに固定）。権限不足等の例外は警告でスキップ。

Changed
- 設計方針の明確化:
  - research / ai モジュールは DuckDB（prices_daily, raw_financials, raw_news 等）に依存し、実行時に本番 API へアクセスしない設計を強調。
  - .env 自動ロードの優先順位を OS 環境 > .env.local > .env としてプロジェクト配布後の安全性を確保。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。

Fixed
- 環境変数・.env のパーシングを強化:
  - export プレフィックス、クォート中のエスケープ、インラインコメント判定（クォートの有無で扱いを分ける）に対応し、.env の柔軟性と堅牢性を向上。
- ポジショニング・配分の丸め・スケーリングでの境界条件を細かく扱うことで合計投下額が available_cash を超えないよう改善。
- run_monitoring / run_execution 起動時にプロセス優先度を最初に設定するようにして、実行中のパフォーマンス安定化を狙う。

Known issues / Notes
- ai/news_nlp.py は堅牢なバッチ・リトライ・書き込みロジックを備えていますが、実運用では OpenAI API レート制限やコスト、JSON レスポンスの堅牢なバリデーション（スキーマ検証）について追加の監視が推奨されます。
- 一部の TODO / 注意点をコード内に残しています（例: position_sizing の price 欠損時のフォールバック、sector_exposure の price 未取得時の扱いなど）。実運用前にこれらのフォールバック実装を検討してください。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用します。Paper Trading と監視 DB を分離したい場合は設定の見直しが必要です。

ライセンス / 貢献
- 初期実装のため、今後の変更は Unreleased セクションに記録してください。リリース前に Breaking Changes は明確に記載します。