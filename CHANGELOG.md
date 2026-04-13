CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開リリース: KabuSys (日本株自動売買システム) を提供。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py に定義）

- 実行コンポーネント
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成をサポート（モック含む）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskConfig のデフォルトパラメータを設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。
    - DuckDB を分析用データベースとして接続して利用。

- 監視コンポーネント
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視データは常に本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定し、ループ内で SystemMonitor.check_once() を呼び出して安全に例外をハンドル。

- 環境設定 / ローダー
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み（OS 環境変数を優先。.env.local は .env を上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化オプション。
    - .env の行パーサが export KEY=val、クォート文字列（エスケープ対応）、コメントの扱い等に対応（堅牢なパース実装）。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE（検証済み値）、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、閾値類、KABUSYS_ENV/LOG_LEVEL の検証等）。

- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。
    - スコアが全てゼロの場合は等配分へフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap により既存ポジションに基づくセクター上限チェックを実装。
    - calc_regime_multiplier により market regime に応じた資金乗数を提供（bull/neutral/bear をサポート、未知はフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装。allocation_method="risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュによる端数配分ロジックを実装。
  - 上記関数は DB 非依存で純粋関数化（ユニットテスト容易化）。

- 研究・ファクター計算（DuckDB ベース）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB のウィンドウ関数を用いて高速に計算。
    - 各種ウィンドウ長（1M/3M/6M、MA200、ATR20、20日平均等）を定数化。
    - データ不足時の None 応答を明確化。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、rank、factor_summary を実装。
    - 外部ライブラリ非依存で実装（標準ライブラリのみ）。

- ニュース NLP / OpenAI 統合
  - news_nlp モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) に対してバッチ（最大 20 銘柄）でセンチメントスコアをリクエスト。
    - API 呼び出しに対するリトライ（429、接続エラー、タイムアウト、5xx）を実装（指数バックオフ、最大リトライ回数）。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分成功時のデータ保護（該当銘柄のみ置換）を考慮。
    - ニュース収集ウィンドウ計算（JST 基準。前日 15:00 ～ 当日 08:30 に相当する UTC 範囲）を実装。
    - OpenAI API キー未設定時は ValueError を送出（明示的なエラー）。

- 監査・検証ツール
  - Paper Trading 検証レポート生成 CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（paper_trading DB）から system_status / trade_logs / risk_logs 等を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db をサポート。DB が存在しない場合のエラーメッセージを表示。
    - P95 の計算・NULL 安全・テーブル未存在時のフォールバックを実装。

- ユーティリティ
  - process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level) で Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度設定。
    - set_cpu_affinity(cpu_count) でプロセスを最初 N コアに固定（権限不足や未対応環境では警告を出してスキップ）。
    - psutil による例外（AccessDenied 等）を安全にハンドリング。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- news_nlp: OpenAI API キーは引数または環境変数 OPENAI_API_KEY で渡す必要あり。未設定時は明示的に失敗する設計（安全性・誤動作防止のため）。

Notes / Design decisions
- 監視機能は常に本番 sqlite_path を使用する（KABUSYS_ENV に依らない）。監視データの一貫性確保のための意図的な仕様。
- Paper Trading 用 DB は本番 DB と完全分離（settings.is_paper 判定により切替）。
- .env ローダは OS 環境変数を保護するため protected セットを持ち、.env.local は既存 OS 変数を上書きしない。
- DuckDB を分析用途に採用（prices_daily / raw_financials テーブル前提）。研究・特徴量計算は外部 API を使わず DuckDB + Python のみで完結。
- 多くの部位は DB 非依存の純粋関数として実装（テスト容易性重視）。

今後の予定（例）
- ユニットテスト補強（position sizing / risk_adjustment 等の端数処理やスケーリングの境界ケース）
- lot_size を銘柄別に対応するためのマスタ拡張
- ai/news_nlp のエラー時の部分的リトライ改善やログ詳細化
- 監視・実行のプロセス管理機能（systemd ユニット例やコンテナ化ドキュメント）

参考
- 各モジュール内の docstring に実装方針・仕様（PortfolioConstruction.md, StrategyModel.md 等）の参照が記載されています。実運用時は該当ドキュメントも併せて参照してください。