Keep a Changelog
===============

すべての変更は https://keepachangelog.com/ja/ の慣例に準拠して記載しています。

Unreleased
----------

- 内部リファクタ / ドキュメント追記
  - モジュール内コメントや docstring を充実させ、各関数の引数・戻り値・副作用（DB参照の有無・IOの有無など）を明確化しました。
  - position_sizing 等に残した TODO / 注意コメントを追加し、将来的な拡張点を明示しました。

0.1.0 - 2026-04-17
------------------

Added
- 初回パブリッシュ: kabusys パッケージ v0.1.0 を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行関連スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト設定を付与（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - エンジンはデーモンスレッドで起動し、data/stop_requested.flag を検知して安全に停止する仕組みを実装。
    - PID ファイル path をサポート（data/execution.pid）。

  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒、1 未満は無効扱いしてデフォルトにフォールバック）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視データは一元管理）。
    - data/stop_requested.flag を検知してループを終了。check_once() 実行中の例外はログに出力して次回に継続。

- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - .env / .env.local の読み込み順序: OS 環境変数 > .env.local (> .env)。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードの無効化が可能。
    - .env パーサーは export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などをサポート。
    - Settings クラスを追加し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、閾値類、KABUSYS_ENV、LOG_LEVEL 等）をプロパティとして取得・検証する API を提供。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の入力値検証を実装（不正値は ValueError）。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選抜。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存保有比率が上限を超える場合、同セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 にフォールバックし警告ログを出力。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づき銘柄ごとの発注株数を算出。
    - リスクベースのポジション算出、単元株（lot_size）丸め、1 銘柄上限・全体投下上限（available_cash）を考慮したスケーリングロジックを実装。
    - cost_buffer を用いた保守的コスト見積り、残余キャッシュを使った端数分配アルゴリズムを実装。
    - 価格欠損時にはスキップしてログ出力（将来: フォールバック価格対応の TODO 記載）。

- 監視・モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_execution/run_monitoring 起動時に呼び出し、監視用テーブルが存在することを保証（冪等）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装し、Windows (HIGH_PRIORITY_CLASS など) と POSIX 系（nice 値）を透過的に扱う。
    - set_cpu_affinity(cpu_count) を追加し、プロセスの CPU affinity を最初の N コアに固定可能（権限不足・未実装 API は警告でスキップ）。
    - 標準的な失敗ケース（AccessDenied / NotImplemented 等）をログで扱う。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を追加。DuckDB のウィンドウ関数を活用して価格・財務データから各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER、ROE 等）を計算。
    - データ不足時の None 処理やカウント閾値チェックを実装。

  - research/feature_exploration.py
    - calc_forward_returns: target_date 基準で将来リターン（複数ホライズン）を計算。horizons 引数の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）なら None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで提供。

- AI ニュース NLP（ニュースのセンチメント自動採点）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ・トークン対策（記事数上限・文字数トリム）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の部分置換（DELETE→INSERT）戦略などを設計。
    - calc_news_window(target_date) を提供し、JST ベースのニュース収集ウィンドウを UTC naive datetime で計算。
    - score_news(conn, target_date, api_key=None) は API キー未設定時に ValueError を発出する仕様。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可（デフォルト: data/paper_trading.db）。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）を集計し、閾値に基づいて PASS/FAIL を出力。
    - P95 計算、日付フィルタ生成、空データに対する安全処理を実装。

Changed
- アプリ起動時のプロセス優先度を起動直後に設定するよう統一（run_execution/run_monitoring が set_process_priority("high") を呼ぶ）。
- monitoring のデフォルトポーリング間隔を 60 秒に設定し、MONITOR_POLL_INTERVAL による上書きを可能にした（不正値は警告してデフォルトにフォールバック）。

Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いを明確化して誤解析を低減。
  - 読み込み失敗時に warnings.warn を出して起動継続するよう改善。

Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護（protected set）する仕組みを導入し、意図しない上書きを防止。

Known issues / Notes
- ai/news_nlp.py の処理は設計的に堅牢化を図っているものの、外部 API 依存のため運用時に API レート・コスト・レスポンス変化への対策（バッチサイズ/プロンプト調整・エラーハンドリングの追加）は監視が必要です。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）については TODO として残してあります。価格欠損が多い環境では投資量が過分に減る可能性があります。
- monitoring は設計上「監視 DB を本番 sqlite_path に固定」しています（環境にかかわらず）。テスト時は意図的に分離する必要があります。
- 一部の OS / 権限環境では set_process_priority / set_cpu_affinity が動作しない場合があります。その際は警告ログが出力され処理は継続されます。

---

補足:
- 本 CHANGELOG は提示されたソースコードから推測できる機能追加・仕様変更・注意点をまとめたもので、実際のコミット履歴や PR 説明が存在する場合はそれらを参照して精査してください。