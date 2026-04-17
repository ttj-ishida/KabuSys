CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[Unreleased]
-------------
- （現時点のコードから明確な「未リリース」差分は推測できないため空白）

[0.1.0] - 2026-04-17
--------------------
初期公開リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。
以下はコードベース（src/kabusys 配下）から推測できる主要な追加・仕様の要約です。

Added
-----
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリング監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル(data/stop_requested.flag)による優雅な終了処理をサポート。
    - 監視は環境変数 KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を明記。
    - SQLite / DuckDB の接続初期化と SystemMonitor.check_once の定期実行。
  - run_execution.py: ExecutionEngine（取引実行エンジン）起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知でエンジンを停止する仕組み。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - src/kabusys/config.py: 環境変数／.env ファイルの読み込みと Settings クラスを実装。
    - 自動 .env 読み込み（プロジェクトルートの .git または pyproject.toml を検出して .env/.env.local を読み込む）。
    - OS 環境変数の保護（.env の上書きを制御）と KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, ログレベル, 環境種別など）。
    - KABUSYS_ENV の有効値は development / paper_trading / live。PAPER_FILL_MODE の有効値: instant/partial/never/reject。

- 監視 DB 初期化ユーティリティ
  - monitoring_db 初期化呼び出しを run_monitoring/run_execution 内で実行して監視テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - Windows / POSIX を吸収するプロセス優先度設定 set_process_priority(level) と CPU affinity 設定 set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフ実装。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合は等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮し、売却予定銘柄は計算から除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知値は警告と 1.0 フォールバック）。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数の決定ロジック（risk_based / equal / score の各方式をサポート）、単元株丸め、aggregate cap に基づくスケーリング、cost_buffer の加味。
  - ポートフォリオ関連関数はすべてメモリ内の純粋関数（DB 非依存）として実装。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを用いた各ファクター計算を実装。
    - 長期移動平均（MA200）や ATR, ボリューム系の指標・ビジネスロジックを考慮した実装。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算。
    - calc_ic: スピアマンランク相関（IC）計算。
    - factor_summary, rank: ランク付け・統計要約ユーティリティ。
  - いずれも DuckDB 接続を受け、外部 API に依存しない設計。標準ライブラリのみで実装。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py:
    - raw_news を集約し OpenAI API（gpt-4o-mini 想定）でセンチメント（-1.0～1.0）を算出して ai_scores に書き込む処理を実装。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン膨張対策（記事数・文字数制限）、429/5xx/ネットワーク等のリトライ（指数バックオフ）を想定。
    - 出力 JSON のバリデーション、スコアの ±1.0 クリップ、部分失敗に対する DB 保護戦略（対象コードのみ置換）などを設計方針として明示。

- ツール: Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py:
    - paper_trading DB を読み、稼働率・注文成功率・送信率・P95 レイテンシ等を計算して標準出力にレポートを出力する CLI ツールを実装。
    - CLI オプション --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を利用可能。
    - Pass/Fail 基準値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）および不備時のメッセージ出力を実装。

Changed
-------
- （初期リリースのため "Changed" はなし）

Fixed
-----
- （初期リリースのため "Fixed" はなし）

Removed
-------
- （初期リリースのため "Removed" はなし）

Security
--------
- OpenAI API キーは明示的に渡すか環境変数 OPENAI_API_KEY を利用する設計（キー未設定時は ValueError を送出して誤動作を防止）。

Notes / Compatibility / Migration
--------------------------------
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。これにより paper_trading 環境でも監視データは本番用 DB に書き込まれるため、意図せず本番 DB に影響を与えたくない場合は運用上の注意が必要です。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用し、本番 DB との完全な分離を図ります。
- .env 読み込み:
  - プロジェクトルート検出に .git または pyproject.toml を使用するため、パッケージ配布後もカレントディレクトリに依存せず動作します。
  - OS 環境変数は既定で保護され、.env.local が .env を上書きする（ただし OS 環境変数は常に優先）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ有効。無効値は起動時に例外を投げます。
- Process priority / CPU affinity 設定は権限不足や未対応プラットフォームで安全にスキップされるようになっています。
- research / portfolio モジュールは純粋関数化されており副作用がなくテストが容易です。

Known issues / TODO
-------------------
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少見積りとなる点について TODO コメントあり。将来的に前日終値や取得原価等のフォールバック価格導入を検討する旨が記載されています。
- ai/news_nlp.py の実装は途中（コード切れが見える）であり、フェッチ／バッチ送信の残り処理が存在する可能性があります。実運用前に完全な実装と統合テストが必要です。
- DuckDB との executemany に関する互換性の注意（空パラメータ集合を送らない確認）があるため、DB 書き込み処理は注意して扱う必要があります。

CLI / 実行例メモ
----------------
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を指定（秒）。
- エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading 環境: KABUSYS_ENV=paper_trading を設定。
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

Copyright
---------
- 本ドキュメントはソースコードの内容から推測して作成した CHANGELOG です。内部実装の細部や未公開の差分については実際のコミット履歴と照合してください。