CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
この CHANGELOG は与えられたコードベースから実装内容を推測して作成しています。

Unreleased
----------

- なし（初期リリース: 0.1.0）

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初回公開リリース。パッケージ名: kabusys、バージョン __version__ = 0.1.0。
  - DuckDB/SQLite を用いたデータ処理・監視・実行パイプラインを含む一連のモジュール群を実装。

- 実行・監視用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - 環境変数 KABUSYS_ENV により paper_trading モードを判別し、paper_trading の場合は paper 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory を介してブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine.run_session() を呼び出す。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py: SystemMonitor のポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。

- 環境設定
  - config.py: Settings クラスを実装し、環境変数やプロジェクトルートの .env/.env.local 自動読み込みをサポート。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどを考慮した堅牢なパース実装。
    - 多数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID_FILE_PATH、KILL_FLAG_PATH、しきい値系など）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。

- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補抽出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコアが全て0の場合等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づく新規候補の除外ロジック（sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト・フォールバックの挙動含む）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく注文株数算出、lot_size による丸め、aggregate cap によるスケーリング（端数配分アルゴリズム含む）、コストバッファ考慮。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を用いた純粋関数。
    - 200日移動平均、ATR、各種モメンタム（1M/3M/6M）等を計算。データ不足時の None 処理。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（horizons の検証あり）。
    - calc_ic, rank, factor_summary: IC（Spearman ρ）計算、ランク付け（同順位平均ランク）、ファクター統計要約を実装。
  - research/__init__.py で主要関数をエクスポート（zscore_normalize は data.stats から参照）。

- AI ニューススコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を計算、ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄／コール）、トークン肥大化対策（記事数上限・文字数上限）、JSON Mode の期待フォーマット、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフとリトライロジック（上限あり）を設計方針として明記。
    - API キー解決（api_key 引数または環境変数 OPENAI_API_KEY）と不足時の ValueError。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピンニングするユーティリティ（引数検証と例外ハンドリングあり）。

- 監視・モニタリング関連
  - monitoring モジュールとの連携（init_monitoring_db を呼び出して監視テーブルを初期化する処理を run_monitoring/run_execution に追加）。
  - run_monitoring がプロセス優先度設定や PID ファイルパスなどを参照して SystemMonitor を駆動。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシなどを算出して判定（PASS/FAIL）を出力。
    - 日付フィルタ（--from/--to）、DB パス（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - P95 計算、各種フォーマット関数、しきい値定義（稼働率 99%、成功率 90% 等）を実装。

Changed
- 設計方針として、リサーチ・AI・ポートフォリオ計算は「DB 参照は限定（prices_daily / raw_financials / raw_news 等のみ）」かつ「本番 API へはアクセスしない」ことを明確化。これにより安全なオフライン検証が可能。
- Settings の .env 自動読込はプロジェクトルート検出（.git または pyproject.toml）に依存するように実装。CWD に依存しない安定したロードを優先。

Fixed
- env パースの堅牢化:
  - export プレフィックス対応、引用符内のバックスラッシュエスケープ処理、インラインコメントの取り扱いにより .env ファイルの微妙なケースに対応。
- calc_forward_returns 等で horizons の入力検証を追加し、不正な値を早期に検出して ValueError を送出するようにした。

Security
- OpenAI API キー取得時に明示的に未設定を検出して ValueError を投げる実装を導入（暗黙の失敗を避けるため）。

Notes / Known limitations
- position_sizing の price フォールバック未実装:
  - apply_sector_cap の注記にある通り、price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり。将来的な拡張で前日終値や取得原価をフォールバックとして用いることを検討。
- ai/news_nlp の API 呼び出しは外部依存のため、ネットワークやレート制限/課金の影響を受ける。失敗時はスキップして継続するようフェイルセーフにしてあるが、部分失敗の扱いに注意が必要。
- 実行系（ExecutionEngine, BrokerClient 等）の詳細実装はこの CHANGELOG の元ソースからは推測できないため、設定パラメータとコンポーネントの組立てに関する記述に留めている。

ライセンス・貢献
- 本 CHANGELOG はコードベースからの推測に基づく要約です。実際の挙動や未公開のコンポーネント（例: 実装ファイルや DB スキーマの詳細）は別途参照してください。