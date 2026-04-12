CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。

v0.1.0 - 2026-04-12
-------------------

Added
- 初期リリース: 基本機能群を追加。
  - 実行 / 監視起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用して本番 DB と分離。
      - 監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。
      - DuckDB を計算用途に接続。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。プロセス優先度を "high" に設定。
      - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の設計（実運用向け）。
  - 環境設定・読み込み
    - config.py
      - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
      - .env/.env.local の読み込み順と上書きルール（OS 環境変数を保護）を実装。
      - export KEY=val 形式、クォート内のエスケープ、インラインコメント処理などをサポートする .env パーサを実装。
      - Settings クラスを追加。多くの設定プロパティ（DB パス、API トークン、監視閾値、環境判定など）を提供し、検証（有効値チェック）を行う。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py
      - シグナル選択（スコア降順）と等重・スコア加重配分の純粋関数を追加。スコアが全て 0 の場合は等重配分へフォールバック。
    - portfolio/position_sizing.py
      - 複数の配分方式（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株（lot_size）丸め、aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した安全弁を備える。
    - portfolio/risk_adjustment.py
      - セクター集中上限の適用（apply_sector_cap）と市場レジームによる乗数計算（calc_regime_multiplier）を追加。未知レジームはフォールバック処理を行う。
  - 研究・ファクター計算
    - research/factor_research.py
      - Momentum / Volatility / Value ファクター計算関数を実装。DuckDB の prices_daily / raw_financials を用いる。
      - 長期 MA・ATR 等は必要行数が不足する場合に None を返すよう安全に実装。
    - research/feature_exploration.py
      - 将来リターンの計算、Spearman ランク相関による IC 計算、ファクター統計サマリを実装。外部ライブラリに依存せず純 Python 実装。
      - rank() は同順位（ties）を平均ランクで扱う実装になっており、丸めによる tie 検出漏れに対応するため round(..., 12) を使用。
    - research パッケージのエクスポートを整備。
  - AI ニュース NLP
    - ai/news_nlp.py
      - raw_news から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
      - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）、API 呼び出しのリトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリッピングを実装。
      - ルックアヘッドバイアス対策のため、内部で datetime.today() / date.today() を参照しない設計。
  - ユーティリティ
    - utils/process_priority.py
      - psutil を用いたプロセス優先度設定ユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収し、安全にフォールバックする。
      - CPU affinity を最初の N コアに固定する機能を追加（set_cpu_affinity）。権限不足時には警告してスキップ。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加。CLI 引数で期間指定可能。
      - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算し、閾値に基づく PASS/FAIL 判定を出力。
      - DuckDB/SQLite のテーブルが存在しない場合でも sqlite3.OperationalError を握りつぶして安全に動作するように実装。

Changed
- 標準的なデフォルトと検証の導入
  - MONITOR_POLL_INTERVAL の不正値に対する警告とデフォルトフォールバック（run_monitoring）。
  - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。不正値は ValueError。
  - KABUSYS_ENV の有効値検証（development/paper_trading/live）。不正値は ValueError。
  - LOG_LEVEL の有効値検証を追加。
- DB 関連の振る舞い
  - 監視用テーブルは起動時に必ず init_monitoring_db() で保証（冪等）。paper_trading でも監視テーブル確保を行うため、監視に依存する機能が安全に動作する。
  - run_monitoring は監視専用に本番 sqlite_path を使う設計（環境に依存しないモニタリング）。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用して完全分離（data/paper_trading.db がデフォルト）。
- .env 読み込み
  - プロジェクトルート探索を __file__ から行うことで CWD 非依存化（パッケージ配布後も動作）。
  - .env/.env.local の読み込み順と protected keys による OS 環境変数保護を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

Fixed
- 安全性・堅牢性強化
  - process_priority の権限不足や未対応 OS に対して警告ログでスキップする挙動に統一。
  - position_sizing の aggregate cap スケーリングで単元株（lot_size）丸めと残差配分の安定化を実装（再現性確保のため二次キーに code を利用）。
  - factor_research / feature_exploration の計算は十分なデータがない場合に None を返すことで downstream が壊れないように配慮。
  - ai/news_nlp の OpenAI API 呼び出しは一部失敗しても他の銘柄の処理を継続し、部分失敗による既存スコアの上書きを防ぐために更新は対象コードに限定して行う。

Notes / Known issues
- 一部の TODO/注意コメント:
  - risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる問題を指摘。将来的に前日終値などのフォールバック価格導入を検討。
  - position_sizing: 将来的に銘柄別単元をサポートするための拡張案あり（stocks マスタに lot_size を持たせる等）。
- ai/news_nlp の振る舞いは OpenAI API の出力形式に依存するため、API 仕様変更やレスポンス異常が発生すると部分的にスコア取得に失敗する可能性がある。堅牢化（より詳細なバリデーションやメトリクス収集）は今後の改善点。

License
- MIT（ソース内に明記がない場合はプロジェクトの LICENSE を参照してください）

以上。