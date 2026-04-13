CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
リリースはセマンティックバージョニングに従います。

Unreleased
----------

（現在のスナップショットでは未リリースの変更はありません。）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリースとして基本機能を追加。
  - パッケージ情報
    - kabusys パッケージのバージョンを 0.1.0 として定義。
      - File: src/kabusys/__init__.py

  - 設定管理 (.env 自動ロード・検証)
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを追加。OS 環境変数は保護され、.env.local は上書き用に優先度を高めて読み込まれる。
    - 読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 独自の .env パーサを実装し、export 構文やクォート、インラインコメント、バックスラッシュエスケープに対応。
    - Settings クラスで主要な環境変数をラップ。値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）と既定値を提供。
      - File: src/kabusys/config.py

  - 実行系：ExecutionEngine 起動スクリプト
    - 実売買/ペーパートレード両対応の起動スクリプトを提供。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用する想定。
    - 依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てとセッション実行を行う。
    - RiskManager に対するデフォルトの RiskConfig を定義（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 閾値、max_drawdown 等）。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを含む。
      - File: src/kabusys/run_execution.py

  - 監視系：SystemMonitor ポーリングループ起動スクリプト
    - 定期的に SystemMonitor.check_once() を呼び出すポーリングループを提供。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する挙動を想定。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを含む。
      - File: src/kabusys/run_monitoring.py

  - 監視 DB 初期化ユーティリティ統合
    - run_execution/run_monitoring から監視テーブルの初期化（init_monitoring_db）を呼び出して、冪等に監視テーブルの存在を保証。
      - 参照: src/kabusys/monitoring/monitoring_db.py（差分外観想定）

  - ユーティリティ：プロセス優先度 & CPU affinity
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。パーミッションや未対応環境は警告を出して安全にスキップ。
      - File: src/kabusys/utils/process_priority.py

  - ポートフォリオ構築
    - 候補選定・重み計算モジュール（select_candidates、calc_equal_weights、calc_score_weights）。
    - セクター集中制限とレジーム乗数（apply_sector_cap、calc_regime_multiplier）。
    - ポジションサイズ決定（calc_position_sizes）: risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケールダウンロジック、cost_buffer による保守見積りを実装。
      - Files:
        - src/kabusys/portfolio/portfolio_builder.py
        - src/kabusys/portfolio/risk_adjustment.py
        - src/kabusys/portfolio/position_sizing.py
        - src/kabusys/portfolio/__init__.py

  - リサーチ / ファクター計算
    - Momentum, Volatility, Value ファクターの計算関数を実装。DuckDB の prices_daily / raw_financials テーブルを想定し、ウィンドウ処理と NULL/データ不足の扱いを明示。
    - forward returns（将来リターン）計算、IC（Spearman ランク相関）計算、ファクターの統計サマリ（count/mean/std/min/max/median）を提供。外部ライブラリに依存せず標準ライブラリと DuckDB で実装。
      - Files:
        - src/kabusys/research/factor_research.py
        - src/kabusys/research/feature_exploration.py
        - src/kabusys/research/__init__.py

  - AI ニュース NLP スコアリング
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎のセンチメント（-1.0〜1.0）を取得し ai_scores テーブルへ書き込む処理を実装。バッチ処理（最大20銘柄/コール）、記事数・文字数のトリム、リトライ（429/ネットワーク/5xx 用の指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分コミットによる部分失敗の耐性を備える設計。
    - ニュース収集ウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST = UTC に変換）。
    - API キー未設定時は ValueError を発生させる明示的チェック。
      - File: src/kabusys/ai/news_nlp.py

  - ペーパートレード検証ツール
    - paper_verification_report CLI を追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を読み込み、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ指標（P95 等）を集計してレポート出力。閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 <= 200 ms）で PASS/FAIL を判定する機能を提供。
      - File: src/kabusys/tools/paper_verification_report.py

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI ニュース機能を利用する場合）
- 主要な動作設定は Settings クラスのプロパティ（SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, KABUSYS_ENV 等）で管理されるため、既存運用環境では .env または OS 環境変数を整備してください。
- Paper Trading 専用 DB は本番 DB と明確に分離されるように設計（デフォルト: data/paper_trading.db）。KABUSYS_ENV=paper_trading で専用 DB と MockBroker を使用します。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正値や 0 以下はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE は instant/partial/never/reject のいずれかを指定してください。無効値は ValueError を送出します。
- .env の自動読み込みにより OS 環境変数が上書きされることを防ぐための保護が入っています。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

Known issues / Limitations
- position_sizing の価格フォールバックは未実装（price が欠損した場合は 0.0 扱い）。将来的に前日終値や取得原価を使用するフォールバックを検討。
- news_nlp 実装は API のレスポンス検証やトランザクション（ai_scores への安全な書き込み）を意図した設計だが、実行時の部分失敗ハンドリングの詳細や OpenAI のレスポンスフォーマット変更に対する追加の堅牢化が必要となる場合がある。
- run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定する試みを行いますが、権限不足や未対応プラットフォームでは警告を出してスキップします。

Security
- 外部 API キー（OpenAI 等）は環境変数で管理することを推奨。コード中にハードコードされたシークレットは含まれていません。

貢献・フィードバック
- 不具合・改善提案は issue を立ててください。今後はテストカバレッジやエラーケースの追加堅牢化、ドキュメント強化を予定しています。