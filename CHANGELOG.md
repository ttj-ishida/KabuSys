CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付は本コードベースから推測可能な初期リリース日（2026-04-12）を使用しています。

[Unreleased]
------------

0.1.0 - 2026-04-12
------------------

Added
- 初期リリースとして以下の主要コンポーネントを追加。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用する（KABUSYS_ENV=paper_trading の場合は data/paper_trading.db を使用）。
    - BrokerClientFactory を利用したブローカークライアント作成、OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせた ExecutionEngine セッション実行を実装。
    - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() で取得して使用。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装。
    - init_monitoring_db を呼び監視用テーブルの存在を保証。
  - 設定 / 環境変数ロード
    - config.py: Settings クラスを追加し、アプリケーション設定（パス、閾値、API トークンなど）をプロパティ経由で提供。
    - .env 自動ロード機構を追加。プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込み、.env.local は .env を上書きする。OS 環境変数は保護され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを強化（export 形式サポート、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等）。
    - 設定検証を追加（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の有効値チェックなど）。未設定の必須環境変数については明示的な例外を投げる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合は等重みへフォールバックして警告を出す。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。"unknown" セクターの扱いやフォールバック動作を明記。
    - portfolio/position_sizing.py: 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash によるスケールダウン）、cost_buffer を用いた保守的見積り、端数分配ロジック（fractional remainder に基づく lot 単位での追加配分）等を実装。
  - ユーティリティ
    - utils/process_priority.py: プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限・未対応 OS 時は警告ログでフォールバック。
  - リサーチ（DuckDB を利用）
    - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。prices_daily / raw_financials テーブルを参照して DuckDB 上で計算。
    - research/feature_exploration.py: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計要約(factor_summary)、ランク変換(rank) を実装。pandas 等に依存せず標準ライブラリで実装。
    - research/__init__.py で上記をエクスポートし、zscore_normalize を data.stats から再公開。
  - AI ニューススコアリング
    - ai/news_nlp.py: raw_news からニュースを集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜+1.0）を算出して ai_scores テーブルへ書き込む機能を追加。
      - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ設計（UTC 変換ロジック calc_news_window）。
      - 最大 20 銘柄/リクエスト、1 銘柄当たりの記事数と文字数上限(_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（上限 _MAX_RETRIES）。
      - レスポンス検証、スコアクリップ（±1.0）、部分失敗時に既存スコアを保護する安全な DELETE/INSERT ロジックを想定。
      - OPENAI_API_KEY 未指定時は ValueError を投げる（必須）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。CLI (--from, --to, --db) を提供し、system_status/trade_logs/risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して判定（PASS/FAIL）を出力。
      - 判定閾値（稼働率 99.0%, 注文成功率 90.0%, 送信率 95.0%, P95 レイテンシ 200 ms）を定義。
      - P95 算出ロジック、データ不足時の N/A 表示、DB ファイル存在チェック、sqlite3.OperationalError を考慮したフォールバック処理を実装。

Changed
- パッケージ初期化
  - __init__.py に __version__="0.1.0" を設定。

Fixed
- N/A（初回リリースのため既知のバグ修正履歴なし）。ただし以下の堅牢化を行った：
  - process_priority と CPU affinity の設定で権限不足や未サポート機能時に例外を吐かず警告でスキップするようにしてデーモン運用での失敗を防止。
  - .env ファイル読み込みでファイルアクセスエラー時に warnings.warn を用いて処理を継続するように変更。
  - DuckDB に対して executemany で空パラメータを渡さないよう注意書きを記載（ai/news_nlp）。

Notes / Migration
- 環境変数の重要事項
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。1 以上の整数を受け付け、無効値はデフォルト 60 秒にフォールバック。
  - KABUSYS_ENV: 有効値は development, paper_trading, live。無効値で起動すると例外となる。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 環境で使用する SQLite DB。デフォルトは data/paper_trading.db。
  - PAPER_FILL_MODE: paper_trading の MockBroker の fill モード。有効値 "instant" | "partial" | "never" | "reject"。デフォルト "instant"。無効値は例外。
  - OPENAI_API_KEY: ai/news_nlp.score_news を使用する際は必須。未設定時は ValueError。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化。
- DB 分離
  - 監視(run_monitoring) は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計。実行系(run_execution) は paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離する。
- 実装上の注意
  - ai/news_nlp.score_news は外部 API を呼ぶため失敗時はスキップ・リトライ等のロジックがあるが、API キーや OpenAI 側のレート制限によって部分的にスコア取得できない場合があり得る。テーブル書き込みは部分成功が他の銘柄へ影響しないよう配慮している。
  - portfolio の position sizing は lot_size（単元株）を前提とした丸めを行うため、細かい単元対応が必要な場合は将来的な拡張（銘柄別 lot_map）を検討すること。

Security
- 現段階で特別なセキュリティ修正は無いが、.env ロード時に OS 環境変数を protected として扱うことで、システム環境変数の誤上書きを防ぐ設計になっている。

開発者向けメモ
- DuckDB / sqlite3 両方の接続を利用している箇所があるため、テスト環境ではそれぞれの DB パスが正しく指し示すファイルを用意すること。
- unit tests を追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env の自動ロードを無効化すると再現性の高いテストが可能。
- news_nlp のテストは OpenAI 呼び出しをモック化すること。モデル応答のバリデーションが厳密のため、モック応答は期待する JSON 形式にする必要がある。

以上。