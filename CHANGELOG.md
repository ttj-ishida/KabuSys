CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-17
------------------

Added
- パッケージ初回リリース。バージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 環境設定管理
  - src/kabusys/config.py: Settings クラスを導入。環境変数・.env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）、読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを強化（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱い）。未設定の必須キー検出で例外を投げる _require() を提供。
  - 各種設定プロパティを提供（DB パス、PID / kill フラグパス、閾値や PAPER_FILL_MODE 等）。KABUSYS_ENV の妥当性検証や LOG_LEVEL 検査を実装。
- 実行系エントリポイント
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、paper_trading 時の専用 SQLite 分離（data/paper_trading.db をデフォルト）、BrokerClientFactory 経由でブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド起動と停止フラグ監視、PID ファイル取り扱いを実装。RiskConfig のデフォルト設定を含む。
- 監視系エントリポイント
  - src/kabusys/run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、0 以下はデフォルトへフォールバック）、監視用 DB 初期化（環境にかかわらず本番 sqlite_path を使用）、停止フラグファイル検出でループ停止。
- モニタリング DB 初期化ユーティリティ（import 経路として監視初期化関数を使用）。
- portfolio（銘柄選定・配分・リスク調整・ポジションサイズ計算）
  - src/kabusys/portfolio/portfolio_builder.py: select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py: apply_sector_cap（既存保有を考慮したセクター集中上限の除外ロジック）、calc_regime_multiplier（レジームに応じた投下資金乗数、未知レジームはフォールバックと警告）。
  - src/kabusys/portfolio/position_sizing.py: calc_position_sizes（risk_based / equal / score の割当方式、lot_size 単位丸め、max_position_pct/aggregate cap、cost_buffer を用いた保守的見積り、合計コストが現金を超える場合のスケールダウンと残差に基づく再配分アルゴリズム）。
  - src/kabusys/portfolio/__init__.py で各関数を公開。
- 研究（Research）モジュール（DuckDB を利用したオンチェーン計算）
  - src/kabusys/research/factor_research.py: calc_momentum（1/3/6 ヶ月リターン・MA200乖離）、calc_volatility（ATR/相対ATR/平均出来高/出来高比率）、calc_value（PER/ROE、raw_financials を参照）。各関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照。
  - src/kabusys/research/feature_exploration.py: calc_forward_returns（任意ホライズンの将来リターン、一括クエリ取得）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median の統計サマリ）。外部ライブラリ非依存で実装。
  - src/kabusys/research/__init__.py にて主要関数を公開（zscore_normalize を kabusys.data.stats からインポートして再公開）。
- AI ニュース NLP（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py: raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に書き込むためのロジックを実装。処理にはニュースウィンドウ計算、記事トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、バッチ送信（最大 20 銘柄 / コール）、JSON Mode 出力のバリデーション、スコアクリップ（±1.0）、エラー時の指数バックオフおよびリトライ、部分的な DB 更新（対象コードのみ DELETE→INSERT）等を備える。API キー解決と未設定時の ValueError を実装。
- ユーティリティ
  - src/kabusys/utils/process_priority.py: set_process_priority（Windows / POSIX の差を吸収して優先度設定、無効値検査、アクセス拒否時の警告）、set_cpu_affinity（最初の N コアに固定、引数検査・許容コア超過時のフォールバック）。psutil ベースのクロスプラットフォーム実装。
- ツール
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。コマンドライン引数 --from / --to / --db をサポートし、P95 計算のためのユーティリティ等を実装。期間フィルタは ISO8601 UTC 文字列で処理。PAPER_TRADING_SQLITE_PATH で DB を指定可能。
- defensive / usability
  - ファイル・DB 存在チェック、SQL の OperationalError を捕捉してフェールセーフ動作（デフォルト値・N/A 表示）、各種ログ出力（INFO/DEBUG/WARNING/EXCEPTION）を充実。

Changed
- 設計方針として、研究・ポートフォリオ関連関数は副作用を持たない純粋関数群として実装（DB 参照は限定的、計算はメモリ内で完結）。
- DuckDB を分析用途に標準採用し、prices_daily / raw_financials 等のテーブルを前提に SQL + Python ハイブリッドで処理。
- 実行 / 監視プロセスは開始時にプロセス優先度を上げる実装（set_process_priority("high")）に統一。

Fixed
- 環境変数パースの耐性向上（不正な MONITOR_POLL_INTERVAL 値 -> デフォルトへフォールバック、.env の引用符とエスケープ処理の強化）。
- position_sizing の合計コストスケールダウン処理において、lot_size 単位での丸めと残余配分を実装し、利用可能現金に合わせた安全な縮小を実現。
- Apply_sector_cap: unknown セクターの扱いを明確化（unknown はセクター上限の対象外とする）。

Notes
- Paper Trading と本番 DB は分離される（settings.is_paper により paper_sqlite_path を使用）。これにより paper_trading 環境での検証が本番データベースへ影響を与えないよう設計されています。
- News NLP は OpenAI API を利用するため、運用時は OPENAI_API_KEY の設定が必要です。API 通信の軽微な失敗はリトライ・スキップでフェイルセーフ化していますが、API 利用コストとレート制限に留意してください。
- 一部モジュールは外部依存（psutil, duckdb, openai）を必要とします。稼働環境にこれらのインストールが必要です。

ライセンス / セキュリティ
- セキュリティに関する変更は本リリースに含まれていません。環境変数や API キーの取り扱いは .env / OS 環境変数を利用する設計です。運用時は秘密情報の管理に注意してください。

--- 

（必要であれば各コミットや変更ファイルごとの詳細な差分要約も追加できます。ご希望があれば出力してください。）