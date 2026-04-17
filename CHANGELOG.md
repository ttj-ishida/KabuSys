KEEP A CHANGELOG
すべての変更は Keep a Changelog の方針に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- なし

[0.1.0] - 2026-04-17
Added
- プロジェクト初期リリースとして以下の主要機能を実装。
  - コアパッケージ:
    - kabusys パッケージ本体（__version__ = 0.1.0）。
  - 実行用スクリプト:
    - run_execution.py: ExecutionEngine を起動するランナー。KABUSYS_ENV = paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB (data/paper_trading.db 既定) を使って本番 DB と完全に分離する。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するランナー。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ / data/stop_requested.flag による安全停止、プロセス優先度設定機能を含む。
  - 設定管理:
    - config.Settings: 環境変数読み込みラッパ。.env/.env.local の自動読み込み（OS 環境変数が優先、.env.local は上書き）をサポート。複数の設定プロパティ（DB パス、PID パス、閾値、環境判定など）を提供。
    - .env パーサーは export プレフィックス、クォート付き値、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - モニタリング / 監査:
    - monitoring_db 初期化を行うヘルパを利用（run_* スクリプトで冪等に init）。
    - run_monitoring は常に本番 sqlite_path を参照（環境に依存せず監視 DB を本番パスで運用）。
  - Execution コンポーネント:
    - ExecutionEngine 起動ロジック（スレッド起動 / 停止フラグ検出 / PID ファイル）。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の組立て例（RiskConfig のデフォルトパラメータを含む）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 用のモック対応を想定）。
  - ポートフォリオ構築ライブラリ (kabusys.portfolio):
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアがゼロの際のフォールバック警告）
    - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに基づく投下乗数）
    - position_sizing: calc_position_sizes（risk_based / equal / score の割当方式、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer 考慮）
    - パブリックエクスポートを __init__ で整備
  - リサーチ / ファクター計算 (kabusys.research):
    - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL ベースの集約）
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（外部ライブラリ不使用で統計量や Spearman ランクを計算）
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計
  - ツール:
    - tools.paper_verification_report: Paper Trading の検証レポートをコマンドラインで生成。稼働率、注文成立率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。期間指定オプションおよび DB パス指定オプションをサポート。DB のテーブル未作成時の耐障害処理あり（OperationalError を捕捉して N/A を表示）。
  - AI ニュース NLP:
    - ai/news_nlp.py: raw_news を集約して OpenAI API (gpt-4o-mini / JSON モード想定) にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルに書き込む処理を実装。バッチサイズ、文字数上限、記事数上限、スコアクリップ、エクスポネンシャルバックオフ（リトライ）などを考慮。
  - ユーティリティ:
    - utils.process_priority: set_process_priority, set_cpu_affinity（Windows / POSIX の差を吸収、権限不足時は警告してスキップ）
    - psutil を利用した優先度 / CPU affinity 設定のラッパ

Changed
- 環境変数読み込みの優先順位を明確化:
  - OS 環境 > .env.local > .env（.env.local は override=True により OS キーを保護した上で上書き）
- PAPER_TRADING 用 DB と本番監視 DB の分離:
  - run_execution は paper_trading 環境で paper_sqlite_path を利用。monitoring は環境にかかわらず本番 sqlite_path を使用するよう明示。
- 設定値のバリデーションを強化:
  - Settings.env, Settings.log_level, PAPER_FILL_MODE などで不正値は ValueError を送出するように変更（安全策）。
- レポート・集計処理での耐障害性向上:
  - paper_verification_report はテーブル未作成時に sqlite3.OperationalError を捕捉してレポートを部分的に生成する（N/A 表示）。

Fixed
- .env パーサーの堅牢化:
  - export キーワード対応、クォート文字内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無で扱いを分離）。
- ポーリング間隔の安全化:
  - MONITOR_POLL_INTERVAL の不正（非整数・0 以下）を検出してデフォルト値にフォールバックし警告を出すように変更。time.sleep に渡す不正値による例外を防止。
- position_sizing / aggregate cap の丸めロジック改善:
  - lot_size 単位での丸めと残余キャッシュを用いた逐次追加配分ロジックを組み込み、再現性のため安定ソートを使用。

Security
- なし

Removed
- なし

Deprecated
- なし

注意事項 / 既知の制約
- ai/news_nlp の処理フローは概ね実装済みだが、外部 API 呼び出し時の完全なエラー処理およびデータベースへの完全置換ロジックは実行時検証が必要（API キー未設定時は ValueError を送出）。
- apply_sector_cap のエクスポージャー計算は price_map の欠損（price=0.0）時に過少見積りとなり得る旨の TODO コメントが残っている。将来的には前日終値や取得原価でのフォールバックを検討すべき。
- DuckDB の executemany に関する制約（バージョン依存の注意点）を文中で考慮しているが、運用環境の DuckDB バージョンでの動作確認を推奨。
- process_priority / set_cpu_affinity は権限がない環境や未対応 OS では警告を出してスキップするため、期待どおりに優先度が設定されない場合がある。
- tools.paper_verification_report は DB のタイムゾーンや timestamp 形式に依存するため、UTC/ローカルの扱いに注意が必要（本実装は ISO8601 UTC 文字列を使用）。

マイグレーション / 注意事項（運用）
- Paper Trading を利用する場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を適切に用意すること。
- OpenAI API を用いる機能を利用する場合は環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡すこと。
- 自動 .env 読み込みを無効化したいテスト等のケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

この CHANGELOG はコードベースの実装内容から推測して作成しています。運用時には実際のコミット履歴やリリースノートと照合してください。