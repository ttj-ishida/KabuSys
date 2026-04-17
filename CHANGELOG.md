CHANGELOG
=========

全体方針
--------
この CHANGELOG は "Keep a Changelog" の形式に準拠して作成しています。  
各項目はコードベース（src/ 以下）の実装内容から推測して記載しています。

Unreleased
----------
- 未完成 / 要対応
  - kabusys/ai/news_nlp.py が途中で切れており、score_news の記事集約フェーズで処理が中断しています（ソース末尾に "if not articl" のような断片が残っている）。このままではニュース NLP の実行が途中で失敗する可能性があります。早急に実装の続きまたは修正を行ってください。
  - position_sizing と risk_adjustment にいくつかの TODO コメント（価格欠損時のフォールバック、銘柄別 lot_size 拡張など）が残っているため、将来的な改善候補として残しています。

[0.1.0] - 2026-04-17
--------------------
初期リリース（コードベースの主要機能を実装）

Added
- 基本アプリケーションメタ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ（デフォルト 60 秒）を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。0以下や不正な値はデフォルトにフォールバックし、警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止判定を実装。
    - 監視処理では環境にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_execution.py
    - ExecutionEngine の起動スクリプト実装。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（data/paper_trading.db 既定）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド実行、停止フラグ監視を実装。
    - 実行 PID ファイル管理（data/execution.pid など）に対応。

- 設定管理
  - config.py
    - Settings クラスで各種環境変数をプロパティとしてラップ（DB パス、API トークン、監視閾値、PID/FLAG パス、環境種別など）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。OS 環境変数を保護する protected 上書きロジックを持つ。
    - .env 行パーサーは export 形式、クォート、エスケープ、行内コメントの取り扱いに対応する堅牢な実装。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外するロジック。
    - レジーム別資金乗数 calc_regime_multiplier を実装（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
      - allocation_method="risk_based" / "equal" / "score" に対応。
      - lot_size（単元）丸め、per-positionの上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer による保守的コスト見積りを実装。
      - スケールダウン後の小数端数処理では残差に基づく lot_size 単位の追加配分を実装し再現性を考慮（順序安定化）。
    - 価格欠損時のスキップやログ出力を行うなど、堅牢性を考慮した実装。

- リサーチ / 特徴量
  - research/factor_research.py
    - モメンタム（calc_momentum）、ボラティリティ・流動性（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB 接続を受け取って実装。
    - 各関数は prices_daily / raw_financials テーブルを参照し、データ不足時は None を返す安全設計。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns、IC（calc_ic）、統計サマリ factor_summary、rank 関数を実装。
    - calc_ic はスピアマンのランク相関を実装し、有効レコードが少ない場合は None を返す。
  - research/__init__.py でエクスポートを整理。

- データベース / 分析基盤
  - DuckDB と SQLite の併用を想定した設計（duckdb_path, sqlite_path を Settings で管理、各起動スクリプトで接続を確立）。
  - monitoring_db.init_monitoring_db を経由して監視テーブルの初期化（冪等）を保証。

- 監視 / 実行ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX を吸収する set_process_priority を実装（psutil 利用）。許可エラー等はログで警告してスキップ。
    - set_cpu_affinity を実装（利用コア数指定による CPU affinity 設定）。不可能な場合は警告を出してスキップ。

- 実行系コンポーネント（雛形）
  - execution 以下に BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager らを組み合わせる起動フローを実装（run_execution が組立てと起動を行う）。
  - RiskConfig のデフォルト値を run_execution 側で設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを実装。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出・出力。
    - 合格基準（稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）を実装し PASS/FAIL の判定を行う。
    - P95 計算、日付フィルタ、DB 存在チェック、OperationalError のフォールバックを備える。

Changed
- N/A（初期リリースのため過去からの変更履歴なし）

Fixed
- 堅牢性改善（初期実装段階での注意点）
  - .env 読み込み時のファイルアクセス失敗を warnings.warn で扱い処理継続するように実装（アプリ停止を避ける）。
  - 設定値のバリデーションを追加（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。不正値に対して明確なエラーメッセージを出す。
  - process_priority / set_cpu_affinity は権限不足や未サポートプラットフォームで失敗しても例外を投げず警告ログでスキップする挙動にして実稼働環境での安全性を高めた。

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の注意
- News NLP（kabusys/ai/news_nlp.py）は OpenAI API を利用する設計だが、ファイル末尾が途中で切れているため現在は実行できない状態です。API キー未設定時は ValueError を送出する実装はあるので、運用時は OPENAI_API_KEY の設定を忘れないでください。
- portfolio モジュールの関数は「純粋関数」を志向しており、DB 参照を行わない設計になっています（ユニットテストや再利用性が高い）。
- DuckDB に対する多数の集計 SQL を使っているため、テーブルスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）が想定通りであることを確認してください。
- run_monitoring は監視用 DB を本番 sqlite_path に固定してアクセスするため、監視の目的で paper_trading 環境を使っても同じ DB に書き込む設計上の意図があります（意図的な分離は run_execution の方で行われる）。

今後の TODO / 改善候補
- kabusys/ai/news_nlp.py の未完部分を実装してエラーハンドリングや部分成功時の DB 保護ロジック（DELETE→INSERT の部分限定更新）を確認する。
- position_sizing の価格欠損時フォールバック（前日終値や取得原価の利用）を追加して、price_map 欠損による過少評価を防ぐ。
- 各種ログレベル・ロギング出力の整理（JSON ロギングや構造化ログへの拡張）。
- 銘柄ごとの lot_size をマスタ化して position_sizing を銘柄別単元対応へ拡張。
- tests（ユニットテスト・統合テスト）の追加（特に financial / research SQL ロジックと news_nlp の API レスポンス処理）。

--- 
（この CHANGELOG はコードの静的解析・読み取りに基づいて作成されています。実際の変更履歴が別途存在する場合は適宜統合してください。）