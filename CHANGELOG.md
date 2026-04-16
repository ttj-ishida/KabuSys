CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and aims to be human- and
machine-readable.

フォーマット: 日本語（Keep a Changelog 準拠）

Unreleased
---------

- （現在未リリースの変更はありません）

[0.1.0] - 2026-04-16
-------------------

Added
- 基本モジュール群を初期実装
  - パッケージバージョンを kabusys.__version__ = "0.1.0" に設定。
- 実行 / 監視の起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用して本番と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag により安全停止可能。
    - 実行 PID ファイル (data/execution.pid) の利用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する仕様。
    - data/stop_requested.flag による停止検知、例外ハンドリング、コネクションクローズを実装。
- 設定管理
  - config.Settings 実装
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）を実装。
    - 読み込み順: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export 形式、クォート、インラインコメント等に対する堅牢なパース実装。
    - 多数の設定プロパティを定義（データベースパス、PID ファイル、監視しきい値、PAPER_FILL_MODE 等）。
    - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証とエラー通知）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights / calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮したスケーリングと再配分ロジックを実装。
    - aggregate cap 超過時のスケールダウンと端数配分ロジックを実装。
- 監視・ユーティリティ
  - utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定関数を実装。
    - Windows と POSIX（Linux, macOS 等）を吸収する実装。権限不足などは警告しスキップ。
- 研究・因子計算（DuckDB ベース）
  - research.factor_research:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER、ROE）を DuckDB SQL で実装。
    - データ不足時の None ハンドリング、ウィンドウバッファなどを配慮。
  - research.feature_exploration:
    - 将来リターン計算（複数ホライズン）、IC（Spearman のランク相関）計算、rank・factor_summary を実装。
    - pandas 等に依存せず標準ライブラリのみで統計量・ランク処理を実装。
  - research.__init__: 必要な関数をエクスポート。
- AI ニュース NLP（OpenAI 経由）
  - ai.news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ calc_news_window を追加。
    - バッチ処理（最大 20 銘柄）、文字数・記事数トリム、429/ネットワーク/5xx のリトライ（指数バックオフ）、JSON レスポンス検証、スコアクリッピング（±1.0）等の安全策を盛り込む設計。
    - （注）ファイルは一部が切れている箇所がありますが、設計と多くの処理は実装済み。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可能）。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等。閾値（稼働率99%、注文成功率90% 等）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ --from / --to、--db オプションをサポート。
- DB/分析補助
  - DuckDB と sqlite3 を併用する設計を導入（monitoring テーブル初期化: init_monitoring_db を idempotent に呼び出す）。

Changed
- なし（初回リリース）

Fixed
- 監視テーブル初期化を冪等にして、Paper Trading 環境でも監視テーブルが存在することを保証（init_monitoring_db を呼び出す実装）。
- .env 読み込み失敗時に警告を出すよう改善（パース読み取り時の例外を捕捉して warnings.warn）。

Removed
- なし

Deprecated
- なし

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で解決する設計。未設定時は明示的に ValueError を発生させることで安全性を確保。

Notes / Implementation details
- 多くの処理は外部状態（DB / API）に依存するため、外部接続失敗時は例外をキャッチして警告・スキップするフェイルセーフ指向で実装されています（監視ループや AI スコアリング等）。
- Paper Trading（シミュレーション）と Live（本番）はデータベースを分離して運用できるよう設計されています。
- DuckDB を用いた因子計算により、価格テーブル（prices_daily）と raw_financials を用いてオンメモリで高速に集計できる設計です。

今後の予定（例）
- ai.news_nlp の未完部分の実装完了（ファイル末尾の処理切れ対応）。
- 単元株（lot_size）を銘柄ごとに持たせる拡張（stocks マスタの導入）。
- テストおよび CI の追加、型アノテーション強化、ドキュメント整備（API リファレンス、設計ドキュメントの公開）。

-----