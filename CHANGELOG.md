CHANGELOG
=========

この CHANGELOG は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
日付はリリース日を示します。コードベースの内容から推測して要点をまとめています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ: kabusys/__init__.py にバージョン "0.1.0" を追加。
- 実行用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離して MockBroker を利用可能にする旨を実装。
    - プロセス開始時にプロセス優先度を "high" に設定。
    - DuckDB を分析用 DB として接続。
    - 注文管理、リスク管理、Reconciler 等のコンポーネント組立てと実行セッション開始を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨を明記。
    - プロセス優先度を "high" に設定してから起動。
    - SQLite / DuckDB コネクションの初期化および安全にクローズ処理。

- 設定管理と自動 .env ロード
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - Settings クラスで各種環境変数をラップ：J-Quants / kabu / LINE / DB パス / 監視閾値 / システムフラグ等。
    - 環境変数のバリデーション実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）とデフォルト値。
    - paper_sqlite_path、sqlite_path、duckdb_path、pid/kill flag path 等を Path 型で提供。

- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選別 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（売却予定銘柄を除外可、"unknown" セクターは上限除外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier 実装（bull/neutral/bear マップ、未知は警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position size 計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング処理を実装。
    - price 欠損時のスキップ、スケーリングに伴う残差配分ロジックあり。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を用いたモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）計算を実装。
    - データ不足時の None 扱いやウィンドウサイズ定義を明記。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、統計サマリ（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリで実装。horizons の入力検証あり。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) に JSON モードでバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装（部分的にファイル末尾で途切れた実装だが設計方針と主要ロジックを含む）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装。
    - API キー解決、バッチサイズ、トークン肥大化対策（1銘柄あたり max articles/chars）、スコアの ±1.0 クリップ、リトライ（指数バックオフ）等のフェイルセーフ設計。
    - 部分成功時に既存スコアを保護するため、更新は対象コードの限定的な削除→挿入方式を想定。

- ツール / レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）で PASS/FAIL を判定。
    - 日付フィルタ、DB 存在チェック、NULL 安全なクエリとフォーマット関数を備える。

- ユーティリティ
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows, Linux/macOS/FreeBSD を吸収）と CPU affinity 設定ユーティリティを提供。
    - 権限不足等の失敗は警告ログでスキップする安全設計。

Changed
- 設計上の注意・挙動明記
  - 監視モジュールは環境に依存せず本番 sqlite_path を使用する（モニタリングデータは本番 DB を参照/記録する方針）。
  - .env の読み込み優先順位は OS 環境変数 > .env.local > .env。OS 環境変数は保護され .env.local による上書きは可能だが OS 環境変数そのものは上書きされない。

Fixed
- 実行時の堅牢性を強化。
  - run_monitoring のポーリングループで check_once() が例外を送出してもループを継続し、例外内容をログ出力して次のポーリングへフォールバックするように変更（フェイルセーフ）。
  - DB 初期化（init_monitoring_db）は冪等に呼び出され、存在しないテーブルがあれば作成することで起動時エラーを低減。

Security
- 外部 API キーの取り扱いについて注意事項を実装。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出し明示的に失敗させることでキー漏洩リスクの誤使用を防止。

Notes / Known limitations
- ai/news_nlp.py は設計と主要処理を含むが、ファイル末尾が途中で途切れているため完全実装（DB 書込の最終処理や一部のエラーハンドリング）はコードベース上で未完の可能性がある。
- price 欠損（0.0）に対するフォールバック価格ロジックは未実装（TODO コメントあり）。これにより一部のエクスポージャー計算が過少評価される可能性がある。
- position_sizing の lot_size は現状グローバル共通（将来的に銘柄別対応を想定した拡張予定あり）。
- research モジュールは DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存するため、データモデルが整備されていることが前提。

References
- 環境変数や設定の例は .env.example を参照する旨が config.py に記載されています。