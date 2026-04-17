Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の慣例に準拠します。主にコードベースから推測した変更点・追加機能を日本語で列挙しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-17
-----------------

初回リリース。主要な機能群とユーティリティを追加しました。

Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API を __all__ で整理（portfolio, execution, monitoring 等）。
- 設定管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検索）。
  - .env と .env.local の読み込みと優先順位制御。OS 環境変数の保護（上書き禁止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - export KEY=val 形式やクォート／エスケープ、行内コメント等に配慮した .env パーサーを実装。
  - 必須環境変数チェックを行う _require()（未設定時は ValueError）。
  - 各種設定プロパティを実装（J-Quants / kabu API トークン、LINE トークン、DB パス、監視しきい値、PAPER_TRADING 用設定等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）とエラー報告。
  - KABUSYS_ENV および LOG_LEVEL のバリデーション。
- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動用エントリポイントを提供。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
  - ブローカークライアント工場（BrokerClientFactory）から Broker を生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - リスクマネージャのデフォルト設定を用意（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - スレッドで engine.run_session を実行し、data/stop_requested.flag による安全停止機構を実装。実行中は execution.pid を利用。
  - 起動時にプロセス優先度を "high" に設定。
  - 監視テーブルが存在しない場合でも init_monitoring_db() による冪等初期化を実行。
- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor ポーリングループのエントリポイント。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視 DB は固定）。
  - 停止フラグ（data/stop_requested.flag）検知でループを抜ける仕組み。
  - check_once() の例外は捕捉してログ出力し、次ポーリングへ継続。
  - 起動時にプロセス優先度を "high" に設定。
- モニタリング DB 初期化（init_monitoring_db を利用）
  - 監視用テーブルが存在することを保証する初期化処理を起動前に行う（冪等）。
- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の違いを吸収してプロセス優先度設定を簡潔に利用可能に。
  - CPU affinity 設定関数を追加（最初の N コアにピン留め）。
  - アクセス権限や未対応 API に対するフォールバック（警告ログ）を実装。
- Portfolio 構築ロジック（src/kabusys/portfolio/*）
  - 候補選定と重み計算（portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に基づく乗数（bull/neutral/bear とフォールバック）を提供。
  - 単元丸め・ポジションサイズ計算（position_sizing）
    - calc_position_sizes: risk_based / equal / score の配分方式に対応し、lot_size（単元）で丸め。
    - risk_based: リスク許容率・損切り率に基づく株数計算。
    - aggregate cap: 利用可能現金を超える場合はスケールダウンし、端数は残差大きい順に lot 単位で再配分。
    - cost_buffer（手数料・スリッページ見積り）を考慮。
- 研究用モジュール（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200乖離を DuckDB 経由で計算。
    - calc_volatility: ATR20 / ATR% / 20日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials と prices_daily から PER / ROE を計算（最新報告期を銘柄ごとに取得）。
    - 全て DuckDB SQL を主体に実装し、営業日ベースの窓を考慮。
  - feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで取得。horizons の妥当性チェックあり。
    - calc_ic: ファクターと将来リターンのスピアマン rank 相関（IC）計算。データ不足時は None を返す。
    - factor_summary / rank: 基本統計量（count/mean/std/min/max/median）とランク処理ユーティリティ。
  - research パッケージの公開 API を整理（zscore_normalize を含む）。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini）に送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み。
  - 処理設計:
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を計算（calc_news_window）。
    - 記事を銘柄ごとに集約し、文字数と記事数の制限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄単位でバッチ送信、JSON Mode で厳密な JSON レスポンスを期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（上限 _MAX_RETRIES）。
    - レスポンス検証、スコアを ±1.0 にクリップ、部分成功時に既存スコアを保護する更新戦略（対象コードのみ DELETE → INSERT）。
  - score_news は OPENAI_API_KEY 環境変数または引数で API キーを受け取る（未設定時は ValueError）。
  - API 失敗時は個別チャンク・銘柄をスキップして処理継続するフェイルセーフ設計。
- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - paper_trading DB（PAPER_TRADING_SQLITE_PATH）から各種指標を集計してレポート出力。
  - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
  - 判定基準（デフォルト）:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - P95 計算、日付フィルタ機能、DB 不在やテーブル欠損時の安全処理を実装。
- DuckDB / SQLite の併用
  - 解析系は DuckDB、動作記録・監視は SQLite を利用する想定で各コンポーネントが接続を受け取る。
- 例外処理とログ
  - 各所で例外を捕捉してログに残し、安全に継続できるよう設計（エンジン監視ループ、AI API 呼び出し等）。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサーの堅牢化（クォート内のバックスラッシュエスケープ、行内コメントの扱い、export プレフィックス対応など）。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対する回復処理（警告ログを出してデフォルトにフォールバック）。

Security
- 環境変数読み込みで OS 環境変数を保護（protected set）することで、外部 .env による既存システム変数の上書きを防止。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Known limitations
- position_sizing の価格フォールバック未実装: price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価等のフォールバック導入を検討している旨のコメントあり。
- news_nlp モジュールは OpenAI API 利用を前提としており、API キーとネットワーク環境が必須。
- process_priority の一部 API（nice / cpu_affinity）は環境により権限不足や未実装の例外が発生する可能性があり、その場合は警告ログを出し処理をスキップする設計。

Authors
- コードベースから推測してドキュメント化しています。実際の貢献者一覧はソースリポジトリのコミット履歴を参照してください。