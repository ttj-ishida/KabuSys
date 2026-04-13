# Changelog

すべての重要な変更はこのファイルに記録されます。  
フォーマットは「Keep a Changelog」に準拠しています。

※ 本リリースはリポジトリ内の現行コードベースから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-13

Added
- 基本パッケージ情報
  - パッケージバージョンを定義: kabusys.__version__ = "0.1.0"。

- 実行エントリ / オペレーショナルユーティリティ
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する挙動（監視 DB を本番 DB と共有する設計）。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority を利用）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory を用いてブローカークライアントを切り替え可能（paper_trading 時は MockBrokerClient を使用する想定）。
    - RiskConfig（デフォルトパラメータを含む）とその初期化（initial_portfolio_value を broker.get_available_cash() で決定）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数読み込み
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - .env のパースロジックを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント取り扱いなどに対応）。
    - Settings クラスを導入し、アプリケーションで使用する各種設定（DB パス、API トークン、PID ファイルパス、しきい値、環境種別判定等）をプロパティで提供。
    - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）と PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH 等のデフォルト値を定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（不正値なら ValueError）。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトで呼び出し。監視テーブルが存在することを保証（冪等処理）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計して判定（PASS/FAIL）を出力。
    - デフォルト DB パスは data/paper_trading.db。コマンドライン引数 `--from` / `--to` / `--db` に対応。
    - P95 計算、各種 NULL/データ欠損に対するフォールバック処理、しきい値はソース内定義（稼働率 99%、注文成功率 90% 等）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック。既存保有のセクター比率を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは警告して 1.0 をフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）での丸め、1 銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer によるコスト見積り調整、端数配分ロジックなどを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）間の差異を吸収してプロセス優先度を設定。権限不足や未対応 OS では警告を出して安全にスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアにピン固定するユーティリティ（引数検証・例外時は警告）。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率 (ma200_dev) を計算。DuckDB の prices_daily を使用。
    - calc_volatility: ATR(20)、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データ（レポート日 <= target_date）を取得して PER, ROE を計算。

  - research/feature_exploration.py
    - calc_forward_returns: target_date から指定ホライズン先の将来リターンを計算（デフォルト horizons=[1,5,21]）。ホライズン検証あり。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）、各ファクターの統計サマリーを提供。外部ライブラリに依存せず標準ライブラリで実装。

  - research/__init__.py
    - 主要関数をエクスポート（zscore_normalize は data.stats から）。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装。
    - ニュース集計ウィンドウ（JST 基準: 前日 15:00 ～ 当日 08:30）を計算する calc_news_window。
    - バッチ処理（1 API コールあたり最大 20 銘柄 _BATCH_SIZE）、記事/文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によりトークン増大に対応。
    - レートリミット・ネットワークエラー・5xx に対しては指数バックオフでリトライ（上限あり）。
    - レスポンス検証、スコアの ±1.0 でのクリップ、部分失敗時に既存レコードを保護する書き込み戦略（必要なコードのみ置換）を採用。
    - API キー未指定時は ValueError を送出。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Notes
- DB：分析系は DuckDB（デフォルト: data/kabusys.duckdb）、運用系の監視/発注ログは SQLite を使用する設計がソース上に反映されている。
- 設計方針のコメントや TODO が多数ソース内に残っており、将来的な拡張（銘柄別 lot_size、価格フォールバック等）が想定されている。
- セキュリティ：機密情報（APIキー等）は Settings 経由で環境変数から読み込む設計。自動 .env ロードを無効化する機能も提供。

今後の改善例（ソース中の TODO / 注意点からの参照）
- position_sizing の price 欠損時のフォールバック戦略（前日終値等）の導入。
- ai/news_nlp の部分失敗時のリトライや部分コミット戦略の強化。
- monitoring と本番 DB の分離や、監視専用 DB を用いる運用オプションの追加検討。