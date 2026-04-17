CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 初回公開リリース。
- 基本的アーキテクチャと実行スクリプトを追加:
  - run_execution.py — ExecutionEngine を起動するエントリポイント。KABUSYS_ENV により paper_trading モード時は専用の MockBroker と DB を使用し、本番 DB と分離する挙動を実装。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を "high" に設定。
- 設定管理モジュール:
  - config.Settings を追加。環境変数（.env / .env.local の自動読み込みを含む）から各種設定値を取得。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 読み込みは OS 環境変数を保護（.env.local は上書き可）し、export プレフィックス・クォート・インラインコメントに対応するパーサを実装。
  - 多数のプロパティを提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, ログレベル, env 判定など）。値バリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights を追加（スコア順ソート、等金額・スコア加重配分）。
  - risk_adjustment.py: apply_sector_cap（セクター集中回避ロジック）、calc_regime_multiplier（market regime に応じた乗数）を追加。
  - position_sizing.py: calc_position_sizes を追加。risk_based / equal / score 各配分方式に対応し、単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer による保守的見積もり、スケーリングロジックを実装。
  - portfolio パッケージの __all__ を定義。
- リサーチ / ファクター計算:
  - research.factor_research: calc_momentum, calc_volatility, calc_value を追加。DuckDB（prices_daily / raw_financials）を用いたファクター算出を行う。
  - research.feature_exploration: calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（Spearman のランク相関による IC）、factor_summary（基本統計量）、rank（同順位平均ランク）を追加。外部ライブラリに依存せず純粋 Python＋DuckDB で実装。
  - research.__init__ で主要関数を公開。
- ニュース NLP（AI）:
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルに書き込む処理を実装。複数銘柄をまとめて処理するチャンクング、トークン肥大対策（最大記事数・最大文字数）、レスポンス検証、スコアの ±1.0 クリップ、エラー（429/ネットワーク/5xx 等）に対する指数バックオフ再試行を備える。タイムウィンドウ計算ユーティリティ（calc_news_window）を提供。
- 実行補助ユーティリティ:
  - utils.process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足等の失敗は警告でスキップ。
- ツール:
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を参照し、期間指定（--from / --to）によりシステム稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を出力する。各種閾値（稼働率 99%, 成功率 90% 等）を定義。
- DB 初期化 / 監視テーブル:
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。run_execution/run_monitoring で起動時に呼ぶよう統合。
- パッケージメタ:
  - kabusys.__init__ に __version__ = "0.1.0" を追加。

Changed
- なし（初回リリースのため新規実装中心）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーの扱い: ai.news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は ValueError を投げて明示するようにした（キー漏洩防止ポリシーを暗黙的に促す）。

Notes / 実装上の重要点
- run_monitoring.py は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」という設計上の挙動を持ちます。これは監視データの一元管理を意図した仕様です（paper_trading の実行系は paper_sqlite_path を使用して本番 DB と分離）。
- run_execution.py は paper_trading モード時に settings.paper_sqlite_path を使うことで、取引ログ等を本番 DB から分離します。
- .env 読み込み: プロジェクトルートはソース配置箇所（__file__ の親）を基準に .git または pyproject.toml で判定するため、CWD に依存しません。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- position_sizing のスケーリング・残差配分は deterministic になるよう安定ソート（code を二次キー）を用いています。
- research モジュールは DuckDB を前提としており、prices_daily / raw_financials テーブルの存在を仮定しています。欠損データ時は None を返す設計で、空データに対しても安全に動作します。
- ai.news_nlp は JSON Mode による厳密な JSON 出力期待とレスポンス検証を行い、部分失敗時に既存のスコアを保護するために更新対象コードを限定して書き換える方針を採用しています。

既知の TODO / 注意点
- 一部の箇所で将来の拡張を示す TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバック処理等）。
- ai.news_nlp の呼び出し時は OpenAI API 利用料とレート制限に注意してください。
- process_priority / cpu_affinity の設定は権限に依存するため、普通のユーザ権限では設定に失敗する場合があります（警告ログが出力され、処理は継続します）。

ライセンス、貢献方法等はプロジェクトルートの該当ファイルを参照してください。