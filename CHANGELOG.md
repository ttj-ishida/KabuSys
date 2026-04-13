Keep a Changelog に準拠した CHANGELOG.md（日本語）
（このファイルはコードベースから推測して作成しています）

All notable changes to this project will be documented in this file.
See: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

変更なし。

[0.1.0] - 2026-04-13
-------------------

Added
- 基本リリース: 初期機能群を追加。
- 実行・監視用エントリポイント:
  - run_execution.py: ExecutionEngine を起動するCLI。KABUSYS_ENV=paper_trading の場合は MockBrokerClient（paper_trading 用 DB を使用）で完全分離して実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定するロジックを組み込み（utils.process_priority.set_process_priority を使用）。
- 環境設定:
  - kabusys.config.Settings クラスを導入。環境変数・.env/.env.local の自動読み込み（プロジェクトルート検出）と、各種設定プロパティ（DBパス、APIトークン、監視閾値、PID/kill ファイルパス、環境判定など）を提供。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースは export KEY=val、引用符、インラインコメントなど多数ケースに対応するカスタム実装を追加。
- データベース接続:
  - sqlite3 と DuckDB の接続を利用（monitoring 用テーブル初期化ユーティリティ init_monitoring_db が存在）。
- Execution コンポーネント群:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）を組み合わせてセッション実行をサポート。RiskConfig の既定値（max_position_pct 等）を設定。
  - Paper trading 用 DB（PAPER_TRADING_SQLITE_PATH）を用いることで本番 DB と分離。
- モニタリング:
  - SystemMonitor を定期的に呼び出す監視ループを実装。エラーはログに記録して次回ポーリングへフォールバック。
- portfolio モジュール（銘柄選定・配分・株数決定・リスク調整）:
  - portfolio_builder: select_candidates（スコア降順・タイブレークの実装）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合に等分配へフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中上限の適用、売却予定銘柄の除外対応）、calc_regime_multiplier（bull/neutral/bear の乗数、未知のレジームは警告して 1.0 にフォールバック）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の allocation_method、lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差処理の再配分ロジック）。
- research モジュール（DuckDB を用いたファクター計算・探索）:
  - factor_research: calc_momentum（1/3/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対ATR、平均売買代金、出来高比率）、calc_value（PER, ROE）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関による IC 計算）、rank / factor_summary（基本統計量）。
  - すべて DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API に依存しない設計。
- AI / ニュース NLP:
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込む処理を追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づき記事を集約、1銘柄あたり記事・文字数の上限を設ける（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄バッチ、JSON Mode の期待出力、スコアを ±1.0 にクリップ、429/5xx/ネットワークエラーに対する指数バックオフでのリトライ、部分失敗時の既存スコア保護（部分置換）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定なら ValueError を送出。
- ユーティリティ:
  - utils.process_priority: set_process_priority（Windows/POSIX の差分吸収）と set_cpu_affinity（最初の N コアに固定）を実装。権限不足や未対応 OS は警告してスキップ。
- ツール:
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値（稼働率 99%、成立率 90% 等）で PASS/FAIL を判定。コマンドラインで日付範囲と DB パスを指定可能。

Changed
- 監視の挙動:
  - run_monitoring は KABUSYS_ENV に依存せず、本番用 sqlite_path を使用する挙動を明示（監視データは本番 DB に記録する方針）。
- .env 自動ロード:
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。プロジェクト配布後も CWD に依存せずに動作する設計。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメント判定などを細かく処理することで一般的な .env パターンに対応。
- 各種計算のエッジケース処理:
  - research / portfolio / tools の関数群でデータ不足やゼロ除算などに対する None 戻しやフォールバック（例: スコア合計が 0 の場合の等分配）を追加して安全性を向上。

Notes（備考）
- DuckDB を多用しており、ファクター・NLP 処理は DB のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, risk_logs, system_status 等）に依存します。マイグレーションやテーブル存在チェックは呼び出し側で行う必要があります。
- 多くの関数は「副作用なし（純粋関数）」を意識して実装されています（特に portfolio/*, research/*）。これにより単体テストが容易です。
- ロギングは各モジュールで適切に行われます。プロセス優先度や CPU affinity の設定は環境依存で失敗する可能性があるため警告にフォールバックします。
- バージョン: kabusys.__version__ == "0.1.0"

今後の改善案（想定）
- 単体テストと CI の追加（DuckDB を利用した統合テスト含む）。
- 銘柄別 lot_size の取り扱い拡張（stocks マスタの導入）。
- ai.news_nlp の出力検証強化、API 呼び出しの部分的リトライ/永続化戦略の改善。
- run_monitoring / run_execution のプロセスマネージメント（systemd ユニット、コンテナ運用）向けの運用ドキュメント整備。

--- 
（以上）