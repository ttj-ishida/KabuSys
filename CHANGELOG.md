Keep a Changelog 準拠の CHANGELOG.md (日本語)
※コードベースの内容から推測して作成しています。実際の履歴と差分がある場合は適宜修正してください。

All notable changes to this project will be documented in this file.

フォーマット:
- 変更はカテゴリ別（Added/Changed/Fixed/Deprecated/Removed/Security）に記載します。
- 各項目には該当するモジュール／スクリプト名や環境変数、デフォルト値等を併記しています。

------------------------------------------------------------
0.1.0 - 2026-04-17
------------------------------------------------------------

Added
- プロジェクト初期リリース相当の機能群を追加。
  - パッケージ情報
    - kabusys/__init__.py: パッケージ定義とバージョン(0.1.0)を追加。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
      - 停止フラグファイル data/stop_requested.flag を検知してループを終了。
      - 監視データ保存に sqlite（settings.sqlite_path）と分析用に DuckDB を使用。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
    - src/kabusys/run_execution.py
      - 実行エンジン起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し Mock ブローカーを利用（本番 DB と分離）。
      - 停止フラグと PID ファイルの取り扱い（data/execution.pid）。
      - ExecutionEngine、OrderManager、RiskManager、Reconciler 等の組み立てとスレッド実行。
  - 設定・環境読み込み
    - src/kabusys/config.py
      - .env/.env.local の自動ロード機能を追加（CWD に依存せずプロジェクトルートを探索）。
      - export 形式や引用符、コメント処理を考慮した .env パーサを実装。
      - Settings クラスを追加し、各種環境変数（DB パス、API トークン、しきい値、環境種別等）をプロパティで提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成 CLI を追加。
      - 指定期間（--from/--to）や DB パス（--db）でのレポート出力をサポート。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標算出と PASS/FAIL 判定基準を実装（閾値はソース内定数）。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 銘柄候補選定（スコア降順）と等金額・スコア加重の重み計算を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
      - Unknown セクターの扱いやログ出力の説明を含む。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing（risk_based / equal / score）を実装。単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer による集計上限調整をサポート。
      - aggregate cap 超過時のスケーリングと残余キャッシュを用いた補正ロジックを実装。
    - src/kabusys/portfolio/__init__.py
      - 上記関数群をパッケージとしてエクスポート。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）を実装。
      - CPU affinity 設定用 set_cpu_affinity を追加。psutil を利用し失敗時は警告でスキップ。
  - リサーチ/ファクター
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いる）。
      - MA200、ATR20、20日平均出来高、複数ホライズンのリターン等を算出。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、統計サマリー（factor_summary）を実装。
      - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
    - src/kabusys/research/__init__.py
      - 主要関数と zscore_normalize（kabusys.data.stats から）をエクスポート。
  - AI ニュース NLP（スコアリング）
    - src/kabusys/ai/news_nlp.py
      - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む実装を追加。
      - バッチ処理（最大20銘柄/コール）、トークン肥大対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx）やレスポンスバリデーション、スコアクリップを考慮。
      - ニュース集計ウィンドウ（JST 基準）の計算ユーティリティ calc_news_window を提供。
      - 注意: 提供されたスナップショットは途中で途切れており、処理の続き（記事集約フェーズ以降）の実装が存在する想定。
  - DuckDB 統合
    - 複数のモジュールが DuckDB を分析用 DB として利用（research, ai, run_* スクリプト等）。

Changed
- 初期リリースなので互換性破壊に関する記載は無し。

Fixed
- 初期リリースのため修正履歴なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーの取り扱いについては、関数引数または環境変数 OPENAI_API_KEY により明示的に供給する設計。デフォルトのハードコーディングは行っていない（セキュリティ配慮）。

Notes / Usage
- 環境変数読み込み
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml が見つかる場所）から読み込む。OS 環境変数が優先される。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（主なもの）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - OPENAI_API_KEY: OpenAI 呼び出し用 API キー
  - PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject）
- 停止制御
  - data/stop_requested.flag（プロジェクトルート data 配下）を作成すると監視・実行プロセスが順次停止する仕組み。
- 注意点（既知の設計コメント）
  - position_sizing、apply_sector_cap 等は price が欠損（0.0）時のフォールバック（前日終値など）は将来的に要改善とコメントあり。
  - news_nlp.py はスナップショットが途中で終わっており、完全な動作確認とユニットテストを推奨。

今後の TODO / 改善案（コード内コメントより推測）
- news_nlp の完全実装と堅牢なエラーハンドリング・部分失敗時のロールバック戦略の確認。
- position_sizing の lot_size を銘柄別対応へ拡張（stocks マスタ参照）。
- price 欠損時の価格フォールバックロジックを追加（前日終値や取得原価）。
- DuckDB の executemany 空パラメータ制約（言及あり）に配慮した処理とテスト。
- CI/テストの整備（環境依存の挙動があるためモックや環境変数制御が必要）。

------------------------------------------------------------
以降のリリースや変更はこのファイルに追記してください。