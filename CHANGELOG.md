CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/) に準拠して記載しています。

現在日付: 2026-04-12

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 全体
  - プロジェクト初期リリース。コア機能（ポートフォリオ構築、ポジションサイジング、ファクター算出、実行エンジン、監視、研究ツール、AI ニューススコアリング、ユーティリティ）を実装。
  - バージョン番号を `kabusys.__version__ = "0.1.0"` として追加。

- 環境・設定
  - Settings クラスを実装し、環境変数から設定値を取得可能にした（J-Quants / kabu API / LINE / DBパス / 監視閾値等）。
  - 自動 .env ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env のパースを強化（export 形式、クォート／エスケープ、インラインコメントの扱いをサポート）。

- 実行 & 監視
  - `run_execution.py` を実装し ExecutionEngine を起動するエントリポイントを提供。paper_trading 環境では専用 SQLite DB（data/paper_trading.db）と MockBrokerClient を使用して本番 DB と完全に分離。
  - `run_monitoring.py` を実装し SystemMonitor のポーリングループを起動。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を参照する挙動を明示。
  - 起動時にプロセス優先度を「high」に設定する仕組みを実行開始直後に呼び出す。

- DB 初期化
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を保証（冪等）。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定: `select_candidates`（スコア降順、同点時は signal_rank の昇順タイブレーク）。
  - 重み算出: `calc_equal_weights`（等金額）、`calc_score_weights`（スコア加重、全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - セクターリスク制御: `apply_sector_cap`（既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外）。"unknown" セクターは上限適用対象外。
  - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対応、未知レジームは 1.0 にフォールバックして警告出力）。
  - ポジションサイジング: `calc_position_sizes`（risk_based / equal / score をサポート、lot_size（単元）丸め、max_position_pct/max_utilization/aggregate cap、cost_buffer による保守的見積り、利用可能資金に応じたスケールダウンを実装）。aggregate スケールダウン時は端数処理により残余キャッシュを有効活用するアルゴリズムを実装。

- リサーチ（kabusys.research）
  - ファクター算出:
    - `calc_momentum`: 1M/3M/6M リターンおよび MA200 乖離率を計算。
    - `calc_volatility`: ATR20、相対ATR、20日平均売買代金、出来高比を計算（true_range の NULL 伝播を慎重に扱う）。
    - `calc_value`: raw_financials から最新財務データを結合して PER / ROE を計算。
  - 特徴量探索:
    - `calc_forward_returns`: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - `calc_ic`: スピアマン順位相関（IC）を実装（None の除外、3 レコード未満は計算不能で None を返す）。
    - `rank` / `factor_summary`: ランク付け（同順位は平均ランク）と基本統計量集計を提供。
  - DuckDB 接続を受け取り SQL + Python で完結する設計（外部 API を参照しない）。

- AI ニューススコアリング（kabusys.ai.news_nlp）
  - OpenAI (gpt-4o-mini) を用いたニュースのセンチメントスコアリング機能を実装。
  - 処理フロー: タイムウィンドウ定義、記事集約（1 銘柄あたり最大記事数／文字数トリム）、バッチ（最大 20 銘柄）で API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗に備えた部分置換（既存スコア保護）を実装。
  - ルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を参照しない設計。
  - API キーは引数または環境変数 OPENAI_API_KEY から取得。未指定時は ValueError を送出。

- ユーティリティ
  - `utils.process_priority`:
    - `set_process_priority(level)` を実装（Windows / POSIX を吸収）。権限不足や未対応 OS の場合は警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` を実装。cpu_count が None の場合は何もしない。無効値チェックと例外ハンドリングを実装。
  - `.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成ツールを実装。稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定する閾値を定義（稼働率 99%、注文成功率 90% 等）。
    - SQL クエリで system_status / trade_logs / risk_logs を参照し、データ欠落時は N/A で扱う。

Changed
- 環境変数の扱い
  - .env のロードで OS 環境変数は保護され、.env.local は .env より優先して上書き可能。
  - Settings.env の値検証（development / paper_trading / live のみ許容）。不正値は例外を送出。

- エラーハンドリング
  - 多くのクエリ・算出処理でデータ不足時に None を返す方針を採用し、上位で表示や判定を柔軟に扱えるように統一。

Fixed
- P95 計算の挙動
  - P95 計算関数 `_p95` が空リストで None を返すように実装し、呼び出し側で N/A を出力可能にした。

- .env パースの堅牢化
  - クォート内バックスラッシュエスケープやインラインコメントの扱い、export プレフィックスの対応により .env の多様な記述に耐性を追加。

- ポジションサイジングの端数処理
  - lot_size（単元）での切り捨て・追加配分ロジックを改善して、aggregate スケールダウン時の再現性と残余キャッシュ活用を向上。

Security
- AI スコアリング
  - OpenAI API キーの取り扱いを引数 / 環境変数の双方で可能にし、未設定時は明示的にエラーにすることで誤用を防止。

Notes / Known issues
- apply_sector_cap のエクスポージャー計算は price_map に 0.0（欠損）を与えた場合、過少見積りされ除外されない可能性がある旨 TODO コメントあり。将来的に前日終値や取得原価をフォールバックに使う改善を検討。
- DuckDB に対する executemany のパラメータ空チェックなど、バージョン差分により追加の互換性対応が必要になる場合がある（コメントで留意）。

Acknowledgments
- 初期実装にあたっては「PortfolioConstruction.md」「StrategyModel.md」等の設計ドキュメントに基づく純粋関数群・アルゴリズムを採用。

--- 

以上はコードベースの実装内容から推測して作成した変更履歴です。記載漏れや誤りがあれば該当箇所（ファイル・関数名）を教えてください。必要に応じて日付・リリースノートの粒度を調整します。