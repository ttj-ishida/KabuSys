CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.
なお、リリース日付はソーススナップショットの取得日（2026-04-16）を使用しています。

Unreleased
---------

- 小さな修正・改善や未リリースの作業はこちらに記載してください。

0.1.0 - 2026-04-16
-----------------

Added
- パッケージ初期リリース相当の機能群を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルを検知して行う。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する旨を明記。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）し、本番 DB と分離。
    - Engine の PID 管理（data/execution.pid）、停止フラグ検知による安全停止処理を実装。
    - ブローカークライアント生成を BrokerClientFactory 経由で行い、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
- 設定管理
  - src/kabusys/config.py: Settings クラスを追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出に基づく）。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
    - 多数の環境変数プロパティを提供（J-Quants / kabu / DB パス / paper_trading 設定 / 監視閾値等）。
    - 必須環境変数未設定時は ValueError を投げる _require() を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- ポートフォリオ構築（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - 銘柄選定 select_candidates、等金額 weight calc_equal_weights、スコア加重 calc_score_weights を実装。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた投下資金乗数）を実装。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer 考慮）。
- 研究・リサーチ機能
  - src/kabusys/research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算を行う。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary、rank を実装。外部ライブラリに依存せず純粋 Python 実装。
  - src/kabusys/research/__init__.py にエクスポートを整備。
- AI ニューススコアリング
  - src/kabusys/ai/news_nlp.py:
    - raw_news -> ai_scores に対する OpenAI API（gpt-4o-mini）によるセンチメントスコア生成処理を追加。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフ・リトライ、レスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）などを設計。
    - calc_news_window ユーティリティでニュース収集ウィンドウ（JST→UTC）を計算。
- ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI ツールを追加。
    - 稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL を判定。
    - DB 欠損やテーブル未存在に対して寛容にエラーハンドリング。
- ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を実装。
    - set_cpu_affinity による CPU affinity 固定も提供。権限不足や未対応環境では警告を出してスキップ。
- 監視 DB 初期化
  - monitoring_db 初期化呼び出しを run_monitoring/run_execution 起動時に追加し、監視テーブルの存在を冪等的に保証。

Changed
- （パッケージ初版のため該当なし）

Fixed
- （パッケージ初版のため該当なし）

Deprecated
- （パッケージ初版のため該当なし）

Security
- 外部 API キー（OpenAI 等）未設定時は明示的にエラーを返す設計（news_nlp.score_news で ValueError）。

Notes / Breaking changes / Migration
- run_monitoring は「監視用途であっても」環境変数 KABUSYS_ENV に関係なく settings.sqlite_path（本番設定）を使う実装になっています。監視データを paper_trading DB に分離したい場合は挙動に注意してください。
- run_execution は KABUSYS_ENV=paper_trading のときに paper_sqlite_path を使用して本番 DB と分離します（paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH で上書き可能）。
- .env 読み込みポリシー:
  - 自動ロード順: OS 環境 > .env > .env.local（.env.local は override=True のため既存 OS 環境を上書きしないが .env の値を上書きする）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 一部関数内に将来対応の TODO コメントあり（例: price のフォールバック、銘柄別 lot_size 拡張など）。運用時は該当箇所の挙動を理解の上利用してください。

Known issues / Limitations
- ai/news_nlp.py は大きな処理フローを実装しているが、ソーススナップショットの末尾が切れているため（ファイル終端の一部欠落）、実行前に完結実装（記事収集 _fetch_articles 等）の存在を確認してください。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる旨の注記があり、現時点ではフォールバック価格ロジックは未実装。
- calc_position_sizes の lot_size はグローバル固定（現状 100）を前提としており、将来的な銘柄別単元対応は未実装。

Contributing
- 貢献・バグ報告・機能要求はリポジトリの issue / pull request へお願いします。README やドキュメントが整備され次第、運用手順や環境変数の例も追加予定です。