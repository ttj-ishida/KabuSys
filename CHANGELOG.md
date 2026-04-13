KEEP A CHANGELOG 準拠の CHANGELOG.md（推測に基づく変更履歴）を日本語で作成しました。プロジェクト内のソースコードから実装内容を読み取り、機能追加・改善点・修正点をまとめています。

注意:
- 実際のコミット履歴がないため、以下はコードの内容から推測して記載した「初期リリース v0.1.0 のまとめ」です。
- 日付は本回答作成日（2026-04-13）を使用しています。実際の公開日やバージョンは必要に応じて調整してください。

CHANGELOG.md
============

フォーマット: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （今後の変更をここに記載）

0.1.0 - 2026-04-13
-----------------
Added
- 基本パッケージ初期実装
  - パッケージメタ情報を追加（kabusys/__init__.py: __version__ = "0.1.0"）。
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定し、適切な SQLite / DuckDB 接続を確立してエンジンを実行。
    - KABUSYS_ENV=paper_trading の際は paper_trading 用の専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッション実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用する設計。起動時にプロセス優先度を設定。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの判定: .git または pyproject.toml）を実装。優先順位: OS 環境 > .env.local > .env。
    - .env パーサーの強化: export 形式対応、クォートあり／なしの処理、インラインコメントの扱い、上書き保護（protected）。
    - Settings クラスを提供。J-Quants / kabu API / LINE / DB パス（DuckDB / SQLite）/監視閾値/環境種別などのプロパティを定義し、入力検証を行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。
- ユーティリティ
  - process_priority.py
    - クロスプラットフォームでプロセス優先度（nice / Windows priority class）と CPU affinity を設定するユーティリティを追加。
    - 権限不足や未対応 OS に対しては警告を出して安全にスキップするフォールトトレラントな実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が閾値を超える場合に候補を除外。unknown セクターは制限対象外にする挙動。
    - 市場レジームに応じた乗数計算（calc_regime_multiplier）：bull/neutral/bear に対応し、未知レジームは警告とともに 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック（calc_position_sizes）を実装。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、全体投下資金の aggregate cap、cost_buffer を用いた保守的コスト見積などを実装。利用可能現金を超える場合はスケールダウンして lot 単位で再配分する処理あり。
- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB を用いたファクター計算を実装（calc_momentum, calc_volatility, calc_value）。
    - momentum: 1M/3M/6M リターン、MA200乖離を計算（データ不足時は None）。
    - volatility: ATR20、ATR割合、20日平均売買代金、出来高比率を計算（必要行数未満は None）。
    - value: raw_financials と価格を組み合わせて PER / ROE を算出（最新財務データの取得は target_date 以前の最新レコードを採る）。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py で主要関数をエクスポート。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを ±1.0 スケールで算出して ai_scores に書き込む処理（score_news）を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供（calc_news_window）。
    - バッチ送信（デフォルト 20 銘柄/回）、トークン肥大対策（記事数・文字数制限）、JSON モードでの厳密なレスポンス検証、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - OpenAI API キー未設定時は ValueError を送出。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。指定期間内の system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95レイテンシ等の指標を算出して PASS/FAIL 判定（しきい値はソースに定義）。
    - P95 の計算、SQL の日付フィルタ、DB 存在チェック、CLI オプション（--from, --to, --db）を提供。
- DB 初期化/統合
  - 監視用のテーブル初期化（init_monitoring_db）呼び出しを適切な箇所で行う（run_execution/run_monitoring）。
  - DuckDB を分析用途に使用するための接続パターンを整備。

Changed
- （初期リリースのため明確な「変更履歴」はなし。将来的なバージョンで差分追記予定）

Fixed
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内エスケープ処理、インラインコメントの扱い、上書き保護の整備により .env からの設定読み込みの信頼性を向上。

Security
- OpenAI API キーの取り扱いに関するバリデーションを追加（未設定時は早期にエラーを発生させる）。
- process_priority / cpu_affinity は権限不足時にスキップして警告を出す仕様とし、例外でプロセスを停止しないように安全性を確保。

Notes / ユーザ向けメモ
- 環境変数の自動読み込みはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- 実行スクリプト
  - 監視: python -m kabusys.run_monitoring（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能）
  - 実行/エンジン: python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- デフォルト DB パス
  - SQLite（監視）: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb
- Paper Trading モード（KABUSYS_ENV=paper_trading）ではブローカーは MockBrokerClient を使い、データは paper_trading 用 DB に記録して本番データと完全分離する設計。

Contributing
- 実装は現時点で機能ごとにモジュール化されています。将来的な変更（API の仕様、DB スキーマ、閾値の調整など）は各モジュールのドキュメント／コメントに従って行ってください。

---- 
以上。必要であればバージョン分け（Unreleased、v0.1.1 など）や特定ファイルごとの詳細な変更点（関数シグネチャの変化、戻り値の仕様など）をより厳密に作成します。具体的なコミット履歴やリリース日があれば、それに合わせて日付・差分を調整できます。