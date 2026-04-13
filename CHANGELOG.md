CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog (日本語訳)
------------------------------------

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ初期リリース。
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 実行エントリ・監視エントリを追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立て、ExecutionEngine.run_session() を呼び出す。
    - duckdb 接続を受け取り Analysis 用データにアクセス可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。
    - 監視機能は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
- 設定管理（環境変数）モジュールを追加。
  - config.py:
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env/.env.local の自動読み込み（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供）。
    - .env パーサは export 形式、クォート文字列、エスケープ、インラインコメントの取り扱いに対応。
    - 環境変数の保護（OS 環境変数を protected として上書き制御）。
    - Settings クラスを追加し、J-Quants / kabu / LINE / DB / 監視閾値 / システム設定等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の検証、PAPER_FILL_MODE の有効値検査、各種パス設定（duckdb/sqlite/paper_sqlite/pid/kill_flag 等）を提供。
- ポートフォリオ構築関連モジュールを追加（純粋関数群、DB 非依存、メモリ内計算）。
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等金額配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは 1.0 として警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数算出。単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差処理（fractional remainder による追加配分）等を実装。
  - portfolio/__init__.py で上記関数群を公開。
- ユーティリティ: プロセス優先度 / CPU affinity 設定。
  - utils/process_priority.py:
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）を吸収して優先度を設定。権限不足や未対応 OS は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン留め機能（None の場合は何もしない）。不正引数は ValueError。
- 研究・ファクター計算モジュールを追加（DuckDB を用いた計算）。
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足は None。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）を計算。true range の NULL 伝播制御や窓サイズ要件を考慮。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算。
  - research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（IC）を実装（ランク付け、ties は平均ランクで処理）。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を提供。
  - research/__init__.py で公開（zscore_normalize を data.stats から再公開含む）。
- AI ニュース NLP スコアリングモジュールを追加。
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約し、OpenAI API（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む想定の実装。
    - スコアリングのタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを提供。
    - API 呼び出しはバッチ（最大 20 銘柄）で実行、JSON Mode 期待、429/ネットワーク/5xx は指数バックオフでリトライ、レスポンス検証、±1.0 にクリップ、部分成功時の DB 書換方式で他銘柄のデータ保護。
    - OpenAI API キー未設定時は ValueError を送出。
- Paper Trading の検証ツールを追加。
  - tools/paper_verification_report.py:
    - SQLite（paper_trading 用）を読み取り Paper Trading の稼働率・注文成功率・送信率・P95 レイテンシ等を集計して標準出力にレポートを出力する CLI を提供。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - --from / --to / --db コマンドライン引数に対応。DB が存在しない場合は分かりやすいエラーメッセージを出力。
    - SQLite 結果が存在しない場合の耐障害性（OperationalError の捕捉）を実装。
- DuckDB / SQLite を組み合わせたデータアクセス設計。
  - 多くの研究・AI モジュールが duckdb 接続を引数で受け、SQL を用いた大規模集計が可能。
- 監視用 DB 初期化ユーティリティを追加。
  - monitoring/monitoring_db.init_monitoring_db を起動前に呼び出して監視テーブル存在を保証（冪等）。

Changed
- なし（初版）

Fixed
- なし（初版）

Removed
- なし（初版）

Notes / Implementation details
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップするため、パッケージ配布後やテスト環境で CWD 依存の問題を避ける設計。
- 多くの関数は DB 参照を行わず純粋関数として実装されており、ユニットテストしやすい構成。
- 実運用では OpenAI API の課金・レート制限や機密情報（API キー）の取り扱いに注意が必要。
- 一部関数に TODO/将来拡張メモ（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバック等）が残されている。

今後の予定（提案）
- テストカバレッジと CI を整備（特に DuckDB クエリの回帰テスト）。
- 実行環境用の systemd / containerization 向け起動スクリプト例の提供。
- AI モジュールのレスポンス検証・エラー時の部分ロールバック戦略の強化。
- 各モジュールのドキュメント（Usage / API / Schema）の追記。

--- 

（この CHANGELOG は、提示されたソースコードの内容から推測して作成しました。リリース日・分類は推定値です。必要であれば実際のコミット履歴やリリースノートに合わせて調整してください。）