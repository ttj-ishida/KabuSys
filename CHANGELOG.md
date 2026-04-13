CHANGELOG
=========

すべての顕著な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- プロジェクト初回リリース。
- 基本アプリケーション情報を追加
  - kabusys.__init__ に __version__ = "0.1.0" を定義。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックしログ警告を出力。
    - 監視処理は環境に関わらず本番用の sqlite_path を使用して DB に接続。
    - プロセス起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory を用いて実際のブローカーまたはモックを切り替え可能。
    - Execution の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。
- 設定/環境変数管理
  - config.py
    - プロジェクトルート自動検出機能を実装 (.git または pyproject.toml を基準)。
    - .env / .env.local の自動読み込み機能を実装（OS 環境変数を保護して .env.local による上書き可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - .env のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 各種 Settings プロパティを提供（J-Quants/Kabu API トークン、DBパス、PID/KILL フラグ、しきい値、環境チェック等）。入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
- ユーティリティ
  - utils/process_priority.py
    - Windows・POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) により high/normal/low を設定（権限不足や未対応 OS は警告ログでスキップ）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン留め（未対応環境は警告でスキップ）。
- Portfolio 構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア重み配分（全スコアが 0 の場合はフォールバックして等配分）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック→超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出。
    - 単元株(Lot)丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケールダウン）、cost_buffer（手数料/スリッページ見積）を実装。
    - aggregate スケールダウン時に残差を lot 単位で再配分するアルゴリズムを実装して再現性を担保。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を提供。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算。
    - 計算は欠損データ取り扱いやウィンドウサイズの検査（十分な行数がない場合は None を返す）を行う。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターン計算（複数ホライズンに対応）。
    - calc_ic: スピアマン順位相関（IC）を計算する機能。データ不足（有効レコード数 < 3）の場合は None を返す。
    - rank, factor_summary: ランク付け（タイは平均ランク）と基本統計量集計を実装（None 値や非有限値を排除）。
  - research/__init__.py に主要 API をエクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI API(gpt-4o-mini) にバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を追加。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換）を実装。
    - バッチサイズや記事/文字数の上限、スコアの ±1.0 クリップ、429/ネットワーク/5xx への指数バックオフリトライ、レスポンスの厳格なバリデーションなどを実装。
    - API キー未指定時は明示的にエラー（ValueError）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加（--from / --to / --db オプション）。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定（閾値はソースに定義）。
    - P95 の計算、日付フィルタ生成、DB 存在チェック・OperationalError 耐性を実装。

Changed
- DB 関連のデフォルトパスを明確化
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH (monitoring): data/monitoring.db（デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- 環境変数ロードの挙動
  - .env/.env.local をプロジェクトルートから自動ロードし、OS 環境変数を保護する仕組みを導入。テストなどで自動ロードを無効化可能。
- ログ出力レベルのデフォルトを INFO に設定した起動スクリプトを追加（run_monitoring/run_execution）。

Fixed
- .env パーサーの改善によりクォートやエスケープ、コメント処理に起因する読み込みミスを修正。
- position_sizing のスケーリング時に再現性を確保するための安定ソート（code を二次キー）を導入。
- research/feature_exploration の horizons 入力検証を追加（正の整数かつ <=252）。

Security
- OpenAI API キー取得時に未設定は速やかにエラーとし、明示的な設定を要求するようにした（ai/news_nlp.py）。

Notes / Known limitations
- apply_sector_cap: price_map に価格が欠損(0.0)の場合、エクスポージャーが過少評価されてしまう可能性がある旨の TODO を残している（将来的に前日終値等でフォールバック予定）。
- calc_position_sizes は現状で全銘柄共通の lot_size を想定している。将来的に銘柄別単元対応の拡張を想定。
- ai/news_nlp の書き込み処理は DuckDB の実行制約（executemany の空パラメータ等）へ注意しているが、部分失敗時の扱いは部分的保護（対象コードで絞って削除→挿入）に留めている。
- DuckDB や SQLite のスキーマや外部モジュール（BrokerClientFactory や ExecutionEngine 実装等）は本リリース内で想定されている形で存在することが前提。

License
- このリポジトリに含まれるコードはリポジトリ本体のライセンスに従います（該当ファイルにライセンス記載がある場合はそちらを参照してください）。

--------------------------------------------------
（注）本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノート作成時は、コミット履歴や issue/ticket 情報を参考に必要に応じて修正・追記してください。