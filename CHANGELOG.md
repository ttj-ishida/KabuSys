# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリに含まれるソースコードから推測して作成した変更履歴です（初回公開相当: v0.1.0）。日付は本ドキュメント作成日です。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys 自動売買システムのコア実装を追加。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - export KEY=val やクォート／エスケープを考慮した .env パース機能（無効行・コメント処理付き）。
    - 読み込み順序: OS 環境変数 > .env.local > .env（OS 環境変数は protected により上書き抑止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境検証等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（development, paper_trading, live）。

- 実行用スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop_requested.flag による外部停止フラグ検知、KeyboardInterrupt 対応、接続クローズ処理。
    - プロセス優先度を起動時に "high" に設定（utils のユーティリティを利用）。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を介したブローカークライアント生成（paper では Mock を利用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てと ExecutionEngine 起動。
    - 停止フラグと execution.pid（PID ファイル）管理、デーモンスレッドでの実行／停止制御。

- 監視 DB 初期化ユーティリティ
  - src/kabusys/monitoring/monitoring_db.py を利用（init_monitoring_db を run スクリプトで呼び出し、監視テーブル存在を保証）。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) : Windows / POSIX を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) : 指定コア数に CPU affinity を固定する機能。
    - psutil の権限エラー等は警告して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等分配にフォールバック（警告出力）。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャーに基づき新規候補を除外するロジック。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告）。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的見積り、残余キャッシュでの端数配分ロジックを実装。
    - price 欠損や 0 値に対するスキップとログ出力。

  - src/kabusys/portfolio/__init__.py に上記関数をエクスポート。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB の prices_daily から計算。
    - calc_volatility: 20 日 ATR, 相対 ATR (atr_pct), 20 日平均売買代金, 出来高比率を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials と prices_daily を結合して PER, ROE を計算（最新財務レコードの取得に ROW_NUMBER を使用）。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - rank, factor_summary: ランク化ユーティリティと基本統計量計算（count/mean/std/min/max/median）。

  - src/kabusys/research/__init__.py で上記関数と zscore_normalize（kabusys.data.stats）をエクスポート。

- AI ニュース NLP（OpenAI 経由のセンチメントスコアリング）
  - src/kabusys/ai/news_nlp.py
    - ニュース収集ウィンドウ計算（target_date に対し JST ベースで前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - raw_news / news_symbols を銘柄別に集約して OpenAI にバッチ送信（最大 20 銘柄 / リクエスト）。
    - gpt-4o-mini を想定、JSON Mode 想定のレスポンス検証、スコア ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（上限）。
    - ai_scores テーブルへの部分置換（対象コードのみ DELETE → INSERT）により他コードのスコア保護。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計。
    - OpenAI API キー未設定時は ValueError。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI。
    - 検証基準（稼働率/注文成功率/送信率/P95 レイテンシ）とデフォルト閾値を定義。
    - SQLite DB（PAPER_TRADING_SQLITE_PATH または --db）から system_status / trade_logs / risk_logs を集計してレポート出力。
    - p95 計算ユーティリティ、日付フィルタの WHERE 句ビルダー、欠損テーブルに対するフォールバック（OperationalError 捕捉）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 読み込み時のファイル読み込み失敗は warnings.warn で通知し安全に継続するように実装（I/O エラーの耐性向上）。
- ポートフォリオ重みがすべてゼロのケースで等分配にフォールバックするロジックを追加（calc_score_weights）。

### Notes / Known limitations / TODOs
- apply_sector_cap の価格欠損時（price_map に値がない場合）にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する TODO コメントあり。
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map への拡張 TODO）。
- DuckDB に対する executemany の制約を意識した実装（ai/news_nlp の DB 書き込みで空パラメータチェックなど）。
- process_priority の優先度設定は権限不足や未対応 OS の場合にスキップされ、警告ログを出力する（OS/権限依存の挙動）。
- ai/news_nlp.py は堅牢性を高めるため多くのエラー条件・バリデーションを実装しているが、API 仕様変更やレスポンス形式の差分に注意が必要。
- run_monitoring は Monitoring 用 DB に常に本番 sqlite_path を使用する設計（意図的な分離）。paper_trading 時のデータ分離は run_execution が担う。

### Dependencies（コード内から推測）
- psutil（プロセス優先度 / CPU affinity）
- duckdb（リサーチ / AI / DB 集計）
- openai（news_nlp の API 呼び出し）
- sqlite3（ローカル DB）
- 標準ライブラリ（logging, os, pathlib, time, threading, datetime, math, argparse 等）

## 参考
- 本 CHANGELOG はソースコードの実装内容・コメントから推測して作成しています。実際のリリースノートや変更履歴と差異がある場合があります。補足・修正の希望があればソースの追加変更点や意図を教えてください。