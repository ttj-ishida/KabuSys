CHANGELOG
=========

全般
----
この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
重要な変更点・追加機能は日本語で記載しています。コードベースから推測した内容を基に作成しています。

Unreleased
----------
（現在のブランチに未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------
初回公開リリース。以下の主要機能・モジュールを追加しています。

Added
-----
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - パッケージエクスポートを定義（portfolio, strategy, execution, monitoring 等の主要サブパッケージを公開）。

- 実行・監視スクリプト
  - run_execution.py:
    - ExecutionEngine の起動エントリポイントを追加。
    - 環境による DB 分離: KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite (data/paper_trading.db または 環境変数で上書き) を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を実行。
    - duckdb への接続をサポート。
    - PID ファイルパスを設定可能（Settings 経由）。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計（監視専用の DB 初期化を実行）。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - .env パーサーを追加（export 形式、クォート・エスケープ、インラインコメント対応）。
    - Settings クラスを実装し、各種設定をプロパティで提供:
      - J-Quants / kabu API / LINE API 関連
      - duckdb_path / sqlite_path / paper_sqlite_path
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
      - 監視関連: pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk 閾値
      - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）
    - settings = Settings() のインスタンスをエクスポート。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
    - set_process_priority(level) を追加（"high" | "normal" | "low"）。
    - set_cpu_affinity(cpu_count) を追加（指定コア数に固定、None で無効）。
    - psutil が原因のアクセス拒否等はログ警告でスキップするフェールセーフを実装。

- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates(buy_signals, max_positions) — スコア降順、同点時は signal_rank でタイブレークして候補抽出。
    - calc_equal_weights(candidates) — 等金額配分。
    - calc_score_weights(candidates) — スコア比率配分。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(...) — セクター集中が上限を超える場合に新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(regime) — market regime に応じた投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes(...) — allocation_method (risk_based / equal / score) による発注株数計算を実装。
    - 単元株（lot_size）丸め、max_position_pct, max_utilization, cost_buffer を考慮した aggregate cap スケーリングを実装。
    - 価格欠損時はスキップし、詳細なログ出力を行う。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum(conn, target_date) — 1M/3M/6M リターン、MA200 乖離率を計算（DuckDB の prices_daily を参照）。
    - calc_volatility(conn, target_date) — ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date) — raw_financials + prices_daily から PER, ROE を計算（最新の財務情報を取得）。
    - DuckDB を利用したウィンドウ関数による効率的な実装。
  - research/feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons) — 将来リターン（fwd_1d, fwd_5d, fwd_21d 等）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンランク相関（IC）を計算（記録数が少なければ None を返す）。
    - rank(values) — 同順位を平均ランクで扱うランク変換関数（丸めによる ties 回避）。
    - factor_summary(records, columns) — count/mean/std/min/max/median を計算する統計サマリ。
    - 外部ライブラリに依存しない純粋実装。

- AI / ニュースNLP
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し ai_scores に書き込むための処理を実装。
    - ニュース取得ウィンドウを計算する calc_news_window(target_date)（JST ベースのウィンドウを UTC に変換）。
    - バッチ処理（バッチサイズ 20）、1 銘柄あたりの記事数・文字数制限、スコアの ±1.0 クリップ、レスポンス JSON バリデーション、Retry（429・ネットワーク・5xx）を備えた堅牢設計。
    - API キー未設定時は ValueError を発生させる。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして他銘柄の処理は継続する設計。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加。CLI (--from, --to, --db) で期間・DB を指定可能。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数などを集計・判定し PASS/FAIL を出力。
    - 各種 SQL クエリと集計ロジックを実装し、データ不足時のフォールバックを考慮。
  - tools/__init__.py を追加（ツールパッケージの存在を確立）。

Changed
-------
- 設定ロードの挙動
  - .env の読み込みはプロジェクトルート検出に依存（__file__ を起点に親ディレクトリを探索）。プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - OS 環境変数は protected として .env/.env.local の上書きを制御。

Fixed
-----
- （初版）実装段階の不整合やハンドリングの強化:
  - .env のクォート・エスケープ処理を改善し、インラインコメントの扱いを正しく処理するようにした。
  - DuckDB の executemany 前に params が空かどうかをチェックする方針（DuckDB の制約を回避するための設計注釈あり）。

Deprecated
----------
- 特になし（初回リリースのため無し）。

Removed
-------
- 特になし（初回リリースのため無し）。

Security
--------
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に渡す必要あり。未設定時は ValueError を発生させる仕様により誤ったデフォルト公開を防止。

Notes / Breaking changes
------------------------
- Settings._require を通した必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に ValueError を送出するため、実行時に環境変数を正しく設定していることが必要です。
- KABUSYS_ENV の値は限定（development, paper_trading, live）されており、無効な値は ValueError を投げます。
- PAPER_FILL_MODE / LOG_LEVEL 等も入力バリデーションを行い、不正値は例外となります。
- run_monitoring は監視用に sqlite_path（デフォルト data/monitoring.db）を用いるため、監視 DB と Paper Trading DB の分離を意図する場合は環境変数を正しく設定してください。

参考: 主なファイル一覧
--------------------
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/ (portfolio_builder.py, risk_adjustment.py, position_sizing.py)
- src/kabusys/research/ (factor_research.py, feature_exploration.py)
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py

以上。必要であれば各ファイルごとのより詳細な変更点（関数単位の説明や既知の制約）を追記します。