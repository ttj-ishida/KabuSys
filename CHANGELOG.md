# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

[Unreleased]
- なし

[0.1.0] - 2026-04-12
-------------------

Added
- 基本パッケージ初期リリース: kabusys (バージョン: 0.1.0)
  - パッケージメタ情報を src/kabusys/__init__.py に追加。
- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合、紙トレード用の専用 SQLite DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成。OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて Engine を起動。
    - RiskManager のデフォルト設定 (最大保有比率, 利用率, rate limit, circuit breaker 等) を明示的に設定。
    - 実行前にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はログ出力の上でデフォルトにフォールバック。
    - 監視用途の DB 初期化（init_monitoring_db）。Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用する点に注意。
    - 実行前にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動ロード機能: プロジェクトルート (.git または pyproject.toml による検出) から .env/.env.local を読み込み。優先順位は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パースの堅牢化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いなどに対応。
    - Settings クラスを提供。主要な環境変数をラップし、値検証を実施:
      - KABUSYS_ENV: development / paper_trading / live のみ許可。
      - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可。
      - PAPER_FILL_MODE: instant/partial/never/reject の検証。
      - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）と閾値（CPU/MEMORY/DISK）をプロパティとして提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUYシグナルのスコア降順ソートと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て0 時は等分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補除外。sell_codes により当日売却予定銘柄を除外してエクスポージャー計算。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。lot_size による丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer を使った保守的コスト見積り、余剰キャッシュを考慮した再配分ロジックを実装。
    - 複数の安全弁（価格欠損時スキップ、lot_size 単位での丸め、_max_per_stock 制約）を実装。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを使用してファクターを算出（MA200、ATR20、各種モメンタム、PER/ROE 等）。
    - ウィンドウ・不足データ時の None 返却等、欠損に対する配慮を実装。
  - research/feature_exploration.py
    - calc_forward_returns, calc_ic, rank, factor_summary を実装。外部ライブラリに依存しない純粋 Python 実装でランク相関（Spearman）や統計サマリを計算。
  - research パッケージは data.stats.zscore_normalize を再公開。
- AIニューススコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols から記事を銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いてセンチメントスコア（-1.0〜1.0）を生成し ai_scores テーブルへ書き込む。
    - 最大チャンクサイズ、トークン膨張対策（記事数・文字数カット）、JSON Mode + 厳密な JSON 検証、スコアクリッピング、429/5xx/ネットワークエラーに対する指数バックオフ再試行などを実装。
    - OPENAI_API_KEY を必須とする（引数による上書き可）。
    - スコア書込は対象コードだけを DELETE → INSERT することで部分失敗時の保護を実施。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows と POSIX 系 (Linux/macOS/FreeBSD) を吸収する実装。psutil を利用し、権限不足や未サポート OS 時は警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツール。CLI (--from, --to, --db) を提供。デフォルト DB は data/paper_trading.db。また検証基準（稼働率, 成功率, 送信率, P95 レイテンシ）を定義し PASS/FAIL を出力。
    - P95 等の統計や欠損時の N/A 表示を実装。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を利用して監視関連テーブルの冪等初期化を行う（起動スクリプトで使用）。
- CLI / スクリプトのエントリポイント
  - main 関数 + if __name__ == "__main__" を各スクリプトに実装して Python -m 経由での起動を想定。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- ai/news_nlp.py は OpenAI API キーの取り扱いを必須とする。API キーは環境変数 OPENAI_API_KEY または関数引数で提供すること。キーの管理は適切な方法で行ってください。

Notes / Known issues / TODO
- monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用パス）を使用します。paper_trading と監視 DB を分離したい場合は運用上の注意が必要です。
- config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを探索します。配布後や特殊構成環境では検出できない場合があり、その際は .env の自動ロードをスキップします（KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に制御可能）。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）だとエクスポージャーが過少見積りされるため将来的に価格フォールバック（前日終値や取得原価）を検討する旨の TODO コメントあり。
- position_sizing:
  - 将来的には銘柄毎の lot_size をサポートするための拡張（stocks マスタに lot_size を持たせる）を想定する TODO コメントあり。
- ai/news_nlp.py:
  - DuckDB の executemany による制約を念頭に置いた処理（params が空でないことのチェック）を行っている。
  - API レスポンスのバリデーションは厳格だが、外部 API の挙動変化により例外的なケースが発生する可能性あり。失敗時はスキップして継続するフェイルセーフ設計。
- utils/process_priority:
  - 権限不足（psutil.AccessDenied）や未実装属性はログで警告し、処理をスキップします。root 権限や適切な権限がない環境では期待どおりに優先度設定が行われない場合があります。
- research モジュール:
  - パフォーマンス確保のため DuckDB の単一クエリで必要なホライズンをまとめて取得する実装だが、データ量や DuckDB のバージョン依存でクエリ最適化が必要となる場合があります。
- テストカバレッジ:
  - 初期実装のためユニット/統合テストやエンドツーエンド運用確認が不十分な箇所があります。特に外部 API 周り (kabu API, OpenAI) と DB スキーマ互換性は実運用前にテスト推奨。

如何にして始めるか (簡単な運用メモ)
- 環境変数の自動ロード:
  - プロジェクトルートに .env を置けば起動時に自動読み込みされます。テストなどで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 監視ループ:
  - python -m kabusys.run_monitoring を使って起動。MONITOR_POLL_INTERVAL でポーリング秒数を設定可能（整数、1 以上）。
- 実行エンジン:
  - python -m kabusys.run_execution を使って起動。紙トレードは KABUSYS_ENV=paper_trading に設定し、PAPER_TRADING_SQLITE_PATH を必要に応じて上書き。
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - または PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB を指定。

参考
- バージョン: src/kabusys/__init__.py にて __version__ = "0.1.0"
- 実装の詳細・設計注記は各モジュールの docstring / コメントを参照してください。