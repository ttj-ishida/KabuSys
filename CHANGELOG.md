CHANGELOG
=========

すべての変更履歴は Keep a Changelog の方針に従って記載します。
セマンティックバージョニングを採用します。

[0.1.0] - 2026-04-16
--------------------

Added
- 初期パッケージを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョンを定義。

- 環境設定 / ロード機能を追加（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
  - .env / .env.local 自動ロード（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env 行の堅牢なパーサ実装（export プレフィクス対応、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメント処理）。
  - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DuckDB/SQLite パス / paper trading 設定 /監視しきい値などのプロパティを提供。
  - PAPER_FILL_MODE（instant/partial/never/reject）などの検証を実装。

- 実行エントリポイントを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカクライアントを生成（paper と live を分離）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - デフォルトの RiskConfig 値を明示（max_position_pct 等）および初期ポートフォリオ値に broker.get_available_cash() を使用。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視 DB を環境で分離しない方針）。
    - 停止フラグファイル検出によりループ終了。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティを参照（monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの存在を保証）。

- Paper Trading 検証ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - CLI: python -m kabusys.tools.paper_verification_report
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db。
  - 指標・閾値:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill_rate) >= 90.0%
    - 送信率 (send_rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - system_status / trade_logs / risk_logs から指標を集計・判定し、PASS/FAIL レポートを標準出力へ出力。
  - P95 計算、日付フィルタ処理、DB テーブル不存在時のフォールバックをサポート。

- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）で抽出。
    - calc_equal_weights / calc_score_weights: 等分配・スコア正規化配分（全スコアが 0 の場合は等分配にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター暴露が max_sector_pct を超える場合、同セクター新規候補を除外）。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method に応じて株数を算出（risk_based / equal / score）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、残差を lot 単位で配分するフェーズを実装。

- 研究・ファクター計算モジュールを追加（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB SQL で計算。
    - calc_volatility: ATR20、ATR%（相対 ATR）、20日平均出来高、出来高比率などを計算（NULL の伝播とカウント制御に配慮）。
    - calc_value: raw_financials から直近財務データを取り、PER / ROE を計算（財務データ欠損は None）。
  - feature_exploration.py
    - calc_forward_returns: 翌日/週/月などの将来リターンを一度のクエリで取得（horizons 検証、最大ホライズンに基づくスキャン範囲の限定）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（ランク処理、ties は平均ランク）。
    - rank / factor_summary: ランク変換・基本統計量サマリ（count/mean/std/min/max/median）。

- AI ニュース NLP スコアリング基盤を追加（src/kabusys/ai/news_nlp.py）
  - raw_news → ai_scores に対するセンチメントスコア付与機能（OpenAI API を使用）。
  - 設計上の特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）をターゲットに記事を集約（calc_news_window）。
    - 1 回の API 呼び出しで最大 20 銘柄をバッチ処理、gpt-4o-mini / JSON Mode を想定。
    - 再試行ロジック（429/ネットワーク/5xx に対する指数バックオフ、最大リトライ数 3）。
    - レスポンス検証（構造・型チェック）、スコアを ±1.0 にクリップ、部分更新の保護（該当コードのみ DELETE → INSERT）。
    - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用（未設定時は ValueError）。
  - （注）score_news の内部実装は記事集約フェーズ以降の処理（_fetch_articles など）を含む設計になっており、コード断片は一部切れているが、バッチ送信・検証・書込を行う仕様であることが確認できる。

- ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - set_process_priority(level): Windows / POSIX の違いを吸収してプロセス優先度を設定（Windows の HIGH_PRIORITY_CLASS、POSIX の nice 値を使用）。許可エラー時は警告でスキップ。
  - set_cpu_affinity(cpu_count): 最初の N コアにプロセスを固定する機能（アクセス権限に失敗した場合は警告でスキップ）。

Changed
- （初期リリースのため該当なし）

Fixed
- .env ローダー: クォート内のバックスラッシュエスケープやインラインコメント処理を明示的に扱うことで、従来の単純パーサが失敗し得たケースの回避を図った（config._parse_env_line）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取扱いは引数／環境変数で明示的に渡す方式を採用。未設定時はエラーを返すことでキー漏洩のミスを検出しやすくしている。

Notes / Migration
- 監視（run_monitoring.py）は KABUSYS_ENV に依存せず常に Settings.sqlite_path を参照します。監視データを環境ごとに分離したい場合は設定やコードの変更が必要です。
- Paper Trading 実行（run_execution.py）では settings.is_paper に応じて paper_sqlite_path を使用します。Paper 環境では本番 DB と完全分離されます。
- .env 自動ロードの挙動を変更したくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- 本リリースでは複数のモジュール（実行系 / 監視 / ポートフォリオ構築 / 研究 / AI ニュース解析 / ツール）をまとめて提供します。各モジュールは外部依存（psutil, duckdb, openai など）を使用しており、実行時に該当パッケージのインストールが必要です。