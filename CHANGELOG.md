CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース。以下の主要コンポーネントを追加。
  - 実行・監視ランチャ
    - run_execution.py: ExecutionEngine 起動スクリプト（スレッド実行、停止フラグ監視、PID ファイル管理）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL にてポーリング間隔上書き可能）。
  - 設定管理
    - kabusys.config.Settings: 環境変数経由の設定取得。.env/.env.local の自動読込（OS 環境変数を保護）、自動読込を無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env パーサ: export 形式やクォート・エスケープ、インラインコメントの扱いに対応する堅牢なパーサを実装。
  - データベース統合
    - sqlite3 / DuckDB を用いたデータアクセス基盤を導入。監視テーブル初期化ユーティリティ（init_monitoring_db）を提供。
    - Paper Trading 用の DB 分離（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）。
  - Execution 関連
    - BrokerClientFactory によるブローカークライアント生成を導入。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てロジックを実装。RiskConfig による各種リスクパラメータを設定可能（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視・運用ユーティリティ
    - utils.process_priority: set_process_priority / set_cpu_affinity を実装。Windows と POSIX 系を吸収し、失敗時は警告でスキップ。
    - 停止フラグ（data/stop_requested.flag）や PID ファイルを用いた安全な起動/停止制御を実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights。
    - portfolio.risk_adjustment: apply_sector_cap（セクター集中の新規候補除外）、calc_regime_multiplier（市場レジームに基づく投下資金乗数）。
    - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score 向けの株数算出、単元株丸め、aggregate cap スケーリング、cost_buffer 対応）。
  - リサーチ機能（DuckDB ベース）
    - research.factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照してファクター算出）。
    - research.feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary, rank。外部ライブラリ未使用で統計処理を実装。
    - research モジュールは zscore_normalize をエクスポート（kabusys.data.stats 経由）。
  - AI ニュース NLP
    - ai.news_nlp: raw_news の銘柄ごと集約、OpenAI（gpt-4o-mini）へのバッチ送信、リトライ（429/5xx/ネットワーク等）とエクスポネンシャルバックオフ、レスポンス検証、±1.0 でクリップして ai_scores テーブルへ安全に書き戻す処理を実装。
    - ニュース収集ウィンドウ計算（calc_news_window）でルックアヘッドバイアスを回避（datetime.today() を参照しない設計）。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト。稼働率・注文成功率・送信率・レイテンシ（P95）等の集計と PASS/FAIL 判定を出力。
      - デフォルト閾値: 稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200ms。
      - --from/--to/--db オプションで期間・DB を指定可能。

Changed
- 実行時のプロセス優先度を起動直後に "high" に設定する運用方針を採用（run_execution/run_monitoring）。
- .env 読込順序: OS 環境 > .env.local > .env（.env.local が上書き）。OS 環境は保護され上書きされない。
- PAPER_TRADING 用 DB を明示的に分離（Settings.paper_sqlite_path）。KABUSYS_ENV が paper_trading の場合は run_execution が paper_trading DB を使用する。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視は本番データへ記録する設計）。

Fixed
- 環境変数パーシングの堅牢化（クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱い）。
- MONITOR_POLL_INTERVAL が不正な値（0 以下や非整数）の場合にデフォルト（60 秒）へフォールバックするように修正。ログで警告を出力。
- 実行中の例外ハンドリングを強化（monitor.check_once の例外はログ出力してループ継続、KeyboardInterrupt による正常終了対応）。
- DB 接続・リソースの確実なクローズを finally ブロックで保証。
- ai.news_nlp の設計で部分失敗時に既存スコアを保護するため、更新は対象コードに絞って DELETE → INSERT する方式を採用（部分的な障害耐性）。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で与える。キー未設定時は明示的なエラーを返す（キーをログに出力しない実装）。
- .env 自動読込は必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時の秘匿性向上）。

Deprecated
- なし

Removed
- なし

Notes / Breaking changes / 注意事項
- 監視（run_monitoring）は意図的に本番 sqlite_path を使用します。開発環境や paper_trading 環境で監視データを分離したい場合は設定を確認してください。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかで、無効な値を設定すると ValueError を送出します。
- set_process_priority / set_cpu_affinity は OS の許可によって失敗する可能性があり、その場合は警告ログを出して処理を継続します。
- DuckDB の executemany 周り（空パラメータ等）の制約に注意して実装しています（ai.news_nlp の書き込みロジック等）。
- tools.paper_verification_report はデータの存在やテーブル構造に依存します。対象 DB に必要なテーブル（system_status / trade_logs / risk_logs）がない場合は N/A 表示や 0 件としてハンドルします。

今後の予定（例）
- ストック毎の lot_size をマスタ管理にして position sizing を拡張
- ai.news_nlp の並列化最適化とレート制御の改善
- DuckDB クエリのパフォーマンス最適化と追加のユニットテスト拡充

-----------

参考: この CHANGELOG はコード内の実装・コメントから推測して作成しています。実際のリリースノートはリポジトリのコミット履歴・変更要件に基づいて調整してください。