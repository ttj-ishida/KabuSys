CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-13
--------------------

初期公開リリース — 基本的な自動売買／研究／監視ユーティリティ群を実装。

Added
- パッケージ初期実装
  - 基本情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - ライブラリ構成: execution, monitoring, portfolio, research, ai, tools, utils, config など

- 実行・監視エントリポイント
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、EngineConfig(date.today()) を用いてセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb 接続も併用。
    - リスク管理のデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec 等）を定義。

  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して状態を記録。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト向け）
    - .env パーサ: export 先頭の対応、クォート内エスケープ、インラインコメント処理、無効行スキップなど多数の実装上の頑健性を提供
    - 各種プロパティ化された設定値: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス (DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH)、PID/KILL フラグ、監視閾値 (CPU/MEM/MEMORY/DISK)、環境バリデーション (KABUSYS_ENV)、LOG_LEVEL 検証、paper_fill_mode 検証 等
    - paper_fill_mode: 有効値の検証（"instant"|"partial"|"never"|"reject"）を行い、不正値は例外

- Portfolio（ポートフォリオ構築）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順（同点は signal_rank 昇順）で上位 N を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア比率で重み付け。全銘柄スコアが 0 の場合は等金額配分にフォールバック（警告出力）
  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: 既存保有のセクターエクスポージャーに基づき、新規候補をセクター制限で除外。unknown セクターは制限適用外。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数。未知レジームは警告のうえ 1.0 にフォールバック。
  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく発注株数計算
    - 単元株（lot_size）単位で丸め、per-position 上限・aggregate cap を実装
    - cost_buffer による手数料/スリッページ見積を考慮
    - available_cash を超える場合はスケールダウンと残余分のロット配分ロジックを実装

- 研究（research）
  - factor_research (src/kabusys/research/factor_research.py)
    - calc_momentum: 1/3/6 ヶ月リターン、MA200乖離を DuckDB の prices_daily から計算
    - calc_volatility: ATR20、相対 ATR、20 日平均出来高、出来高比率を計算
    - calc_value: raw_financials と prices_daily から PER / ROE を計算（最新報告書を特定して結合）
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算（LEAD を使用）
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。有効レコードが 3 未満の場合は None を返す
    - rank, factor_summary: ランク付け・統計サマリユーティリティ
  - research パッケージエクスポートに zscore_normalize（kabusys.data.stats から）を追加

- AI / ニュースNLP
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news を集約して OpenAI (gpt-4o-mini) を用いて銘柄ごとにセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装
    - タイムウィンドウ計算（JST の 前日 15:00 〜 当日 08:30 を UTC に変換）
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数上限でトリム、スコアクリップ、レスポンス検証
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ（_MAX_RETRIES 等で制御）
    - API キー未設定時は明示的例外を送出
    - フェイルセーフ設計: API 失敗時に部分的にスキップして他処理は継続する方針

- ツール
  - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading 用検証レポート生成スクリプト
    - コマンドラインから期間指定可能（--from / --to / --db）。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能
    - システム稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数などを計算して PASS/FAIL 判定（閾値はソース内定義）
    - P95 計算、各種 SQL クエリに対して OperationalError を捕捉して安全にフォールバック

- ユーティリティ
  - process_priority (src/kabusys/utils/process_priority.py)
    - set_process_priority: Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、psutil を用いて nice / priority を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数にプロセスを pin する機能（利用不可/権限不足時は警告を出してスキップ）

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Security
- 環境変数依存の設定値（API キー等）は必須チェックを行う箇所あり（例: OpenAI、J-Quants、Kabu API パスワード）。運用時は .env の取り扱いに注意してください。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト・CI 等で利用）

Notes / Migration
- 監視（run_monitoring）は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading 環境でも監視用 DB は本番パスを参照する点に注意してください。
- 実行（run_execution）は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- MONITOR_POLL_INTERVAL を環境変数で指定できます（秒）。1 未満・不正値は無視され 60 秒が使われます。
- paper_fill_mode の有効な値は "instant" / "partial" / "never" / "reject" です。不正値は起動時に例外を発生させます。
- .env の読み込み順・上書きルールは OS 環境変数を優先し、.env.local は .env を上書きします（ただし OS 環境変数は保護されます）。

Acknowledgements / Implementation remarks
- DuckDB を分析用途に、SQLite を軽量な運用データ保存に使用するハイブリッド設計。
- 多くの関数は副作用を持たない純粋関数として設計（Portfolio / Research モジュール等）。
- OpenAI クライアントは明示的な API キー提供または環境変数 OPENAI_API_KEY を期待します。API 呼び出しの失敗があっても他の処理を継続するフェイルセーフな設計。

--- 

今後の予定（例）
- モジュールの単体テスト充実化
- news_nlp のレスポンス検証・エラー処理の更なる堅牢化と部分コミット戦略のテスト
- 銘柄別 lot_size や価格フォールバックロジック等の拡張
- ドキュメントの追加（API 使用法・運用手順・データスキーマ）