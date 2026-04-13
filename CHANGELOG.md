CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」フォーマットに準拠します。  
セマンティックバージョニングを使用します。

0.1.0 - 2026-04-13
-----------------

Added
- パッケージ初期リリース相当の機能群を追加。
  - 全体
    - パッケージバージョンを __version__ = "0.1.0" として定義。
    - ロギングを基本設定 (INFO) で利用する起動スクリプトを提供。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告を出してデフォルトにフォールバック。
      - 監視処理は環境設定にかかわらず本番 sqlite_path を使用する仕様（監視データは本番用 DB に記録）。
      - プロセス優先度を起動時に "high" に設定（set_process_priority を呼び出す）。
      - sqlite3 / DuckDB 接続を確立し、init_monitoring_db による監視テーブル初期化を行いポーリングループを実行。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離してモックブローカーが利用可能。
      - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）が設定済み。初期ポートフォリオ値は broker.get_available_cash() による取得を利用。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定 (kabusys.config)
    - Settings クラスを実装し、各種環境変数をラップ（J-Quants / kabuAPI / LINE / DB / 監視 / システム設定など）。
    - .env 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml により探索）。.env と .env.local の読み込み順、OS 環境変数保護（上書き不可）に対応。
    - .env パーサの改良:
      - export KEY=val 形式対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空白を考慮したコメント認識。
    - 設定項目にバリデーションを導入（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - デフォルトパス: DUCKDB_PATH (data/kabusys.duckdb)、SQLITE_PATH (data/monitoring.db)、PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) など。
  - ユーティリティ (kabusys.utils.process_priority)
    - set_process_priority(level) を実装。Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、適切な nice 値や Windows 優先度クラスを設定。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は無効化）。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順・タイブレークで並べ上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコアが全て 0 の場合は等配分へフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限を適用（既存保有を考慮、売却予定コード除外、"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をマッピング、未知レジームは警告の上 1.0 にフォールバック）。
    - position_sizing:
      - calc_position_sizes: リスクベース／equal／score の配分方式に対応。lot_size（単元）で丸め、単銘柄上限・aggregate cap のスケーリング、cost_buffer（スリッページ等）を考慮した保守的な見積りを実装。価格欠損時はスキップ。
  - 研究用モジュール (kabusys.research)
    - factor_research:
      - calc_momentum / calc_volatility / calc_value を実装。DuckDB 上の prices_daily, raw_financials テーブルを参照してファクター（モメンタム、ATR、流動性、PER/ROE 等）を計算。ウィンドウ不足時は None を返すなど堅牢に設計。
    - feature_exploration:
      - calc_forward_returns: 将来リターンを複数ホライズンで一括取得。
      - calc_ic / rank / factor_summary: IC（Spearman）計算、ランク付け、統計サマリーを標準ライブラリのみで実装。
    - research パッケージ __all__ で zscore_normalize を含む外部ユーティリティをエクスポート。
  - AI ニュース NLP (kabusys.ai.news_nlp)
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント判定し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む仕組みを実装。
    - 処理詳細: タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30）、記事集約、バッチ（最大 20 コード）で API 呼び出し、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンスバリデーション、スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護するためコード絞り込みで置換。
    - OpenAI API キーの解決は引数優先→環境変数 OPENAI_API_KEY。未設定時は ValueError。
  - ツール (kabusys.tools.paper_verification_report)
    - Paper Trading 検証レポート生成スクリプトを追加。
    - CLI オプション: --from/--to/--db。デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算。閾値（デフォルト）に基づく PASS/FAIL 判定を出力。
    - P95 の計算、NULL 安全な SQL 実行、DB 不存在時の明示的エラーメッセージなどを実装。

Changed
- （初回リリースのため特になし）

Fixed
- 環境変数パーサの堅牢化により、クォート内エスケープやインラインコメントの誤解析を修正。
- MONITOR_POLL_INTERVAL の無効値（非整数や 0 以下）を安全に扱い、ValueError によるクラッシュを回避してデフォルトへフォールバックするように修正。
- DuckDB executemany など一部実行時制約（空パラメータ等）を考慮した防御的実装。

Deprecated
- （初回リリースのため特になし）

Removed
- （初回リリースのため特になし）

Security
- OpenAI API キーや重要な値は環境変数 / .env を通じて管理する想定。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。

注記
- 本リリースは機能群の初期実装に相当します。実行には外部依存（psutil, duckdb, openai, sqlite3 等）が必要です。実環境へデプロイする際は環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を適切に設定してください。
- 監視・実行スクリプトはいずれも起動時にプロセス優先度変更を試みます。権限がない環境では警告が出て処理を継続します。

References
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/
- Semantic Versioning: https://semver.org/