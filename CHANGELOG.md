CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。セマンティックバージョニングを使用します。

[Unreleased]
-------------

- なし（初回リリースに向けたスナップショット）

[0.1.0] - 2026-04-12
-------------------

Added
- 基本パッケージと初回リリース相当の機能を追加。
  - パッケージ情報
    - kabusys.__version__ を 0.1.0 に設定。
  - 設定管理 (kabusys.config.Settings)
    - .env / .env.local の自動ロード（プロジェクトルート判定: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env の堅牢なパース実装（export プレフィックス対応、引用符内のエスケープ、行内コメントの扱い等）。
    - 必須環境変数チェック(_require)と各種プロパティ提供（J-Quants / kabu API / DB パス / PID/KILL フラグ /閾値 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - 環境モード（development / paper_trading / live）とログレベル検証。
  - 実行系エントリ
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading のときは専用の paper_trading DB を使用（data/paper_trading.db がデフォルト）し、MockBroker を利用する想定で本番 DB と完全分離。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority 呼び出し）。
      - ExecutionEngine の組立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）。
      - RiskManager に渡すデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視系エントリ
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
      - 起動時にプロセス優先度を "high" に設定。
      - monitoring DB の初期化（init_monitoring_db）と DuckDB 接続。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
      - --from / --to / --db オプション対応。
      - 稼働率 / 注文成功率（fill_rate） / 送信率 / レイテンシ（avg/max/P95） / リスク却下数を集計し、PASS/FAIL 判定を出力。
      - デフォルト閾値: 稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
  - ポートフォリオ構築（kabusys.portfolio）
    - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - risk_adjustment: セクター上限除外（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - position_sizing: 株数算出ロジック（calc_position_sizes）。
      - allocation_method による多様な配分（risk_based / equal / score）。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap・cost_buffer（手数料/スリッページ見積り）考慮。
      - available_cash に合わせたスケールダウンと端数補正ロジック実装（残差順で lot 単位追加配分）。
  - 研究用モジュール（kabusys.research）
    - factor_research: モメンタム / ボラティリティ / バリューのファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。
      - モメンタム: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
      - ボラティリティ: ATR20、相対ATR、20日平均売買代金、出来高比率。
      - バリュー: PER / ROE（最新の raw_financials を参照）。
    - feature_exploration: 将来リターン calc_forward_returns、IC（Spearman）calc_ic、統計サマリー factor_summary、ランク生成 rank。
      - forward returns は複数ホライズンをまとめて効率的に取得。
      - calc_ic は ties を平均ランクで扱い、3 サンプル未満で None を返す。
  - AI ニュース NLP（kabusys.ai.news_nlp）
    - raw_news を OpenAI (gpt-4o-mini) でセンチメント解析し ai_scores テーブルに格納する機能を追加。
    - 日時ウィンドウ計算 (前日 15:00 JST 〜 当日 08:30 JST に相当する UTC 範囲)。
    - 銘柄ごと記事集約、1 銘柄あたり記事・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を設けトリム。
    - 最大 20 銘柄単位でバッチ送信、JSON Mode 期待のレスポンスを検証してスコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx の際は指数バックオフでリトライ（上限あり）。
    - API キー未設定時は ValueError を送出。
  - ユーティリティ（kabusys.utils.process_priority）
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX の差分吸収（psutil 利用）と、権限不足等の失敗時には警告ログを出して安全にスキップ。

Changed
- 環境・DB の既定動作の明確化
  - 監視（run_monitoring）は KABUSYS_ENV に依存せず常に settings.sqlite_path（本番用）を使用する設計を明記。
  - 実行系（run_execution）は paper_trading 環境を検出すると paper_sqlite_path を使用し DB を分離。
- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順に適用。既存の OS 環境をプロテクトする実装。
- ログ出力 / 起動時処理
  - run_monitoring/run_execution 起動時にプロセス優先度を設定するよう統一。

Fixed
- .env パーサの堅牢化
  - export キーワードの対応、引用符内のエスケープ処理、行内コメントの挙動改善により .env の柔軟性と互換性を向上。
- 報告系の欠損データ対応
  - paper_verification_report のクエリでテーブル欠如やデータ不足時に例外を起こさず N/A 表示でフォールバックする実装。
- research/feature_exploration のランク処理
  - ランク生成で浮動小数の丸め誤差を回避するため round(v, 12) を使用し ties の正しい扱いを保証。

Security
- OpenAI API の利用に関して
  - news_nlp.score_news は API キーが未設定の場合に即時エラーとし、不正な既定動作を防止。
- プロセス優先度設定失敗時は詳細をログ出力して処理継続（アクセス権限問題でプロセスが停止しないように安全化）。

Notes / Caveats
- ai/news_nlp の処理は外部 API（OpenAI）へ依存するため、API レート制限やコスト、プライバシー取り扱いに注意してください。
- position_sizing の価格欠損（price == 0.0）の場合、現在は単純にスキップしており、将来的に前日終値や取得原価によるフォールバックを検討する旨をコード中に注記しています。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値（0 以下や非数）が設定された場合にデフォルト値(60s)へフォールバックして安全に動作します。

References
- 各モジュールの詳細挙動はソースコード内のドキュメンテーション文字列（docstring）とコメントを参照してください。