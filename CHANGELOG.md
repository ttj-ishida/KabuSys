Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在の状態
---------
- Unreleased: 今後の変更予定
- 0.1.0 - 2026-04-16: 初回リリース相当（コードベースの現状を基に推測して作成）

Unreleased
----------
（現時点で未リリースの変更はありません。将来の修正や改善はここに追記してください。）

0.1.0 - 2026-04-16
------------------

Added
- 全体
  - パッケージ初期リリース相当の機能群を追加。
  - __version__ を 0.1.0 に設定。

- 設定・環境変数読み込み (kabusys.config)
  - .env / .env.local の自動読み込みを実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーを強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートとバックスラッシュエスケープ処理をサポート
    - インラインコメントの扱い（クォート有無で挙動を分離）
  - Settings クラスを導入し、アプリ設定をプロパティ経由で取得可能に:
    - DB パス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH)
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - 各種監視閾値・ファイルパスプロパティ（pid/kill flag 等）
  - settings インスタンスをエクスポート。

- 実行・監視エントリポイント
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。設定に応じて paper_trading 用 DB を分離して使用。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - デフォルトの RiskConfig を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値を broker.get_available_cash() から取得。
    - 実行はスレッドで行い、プロジェクトルートの data/stop_requested.flag を監視して安全に停止可能。
    - PID ファイルの取り扱い（data/execution.pid）をサポート。
    - 監視テーブルの初期化（init_monitoring_db）を起動前に呼び出し、冪等的に存在を保証。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告を出しデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を High に設定（set_process_priority を使用）。
    - data/stop_requested.flag の存在検知でループを終了。

- 監視 DB 初期化
  - monitoring_db の初期化呼び出しを各起動スクリプトから行い、system_status などのテーブルが存在することを保証。

- ツール: Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
  - Paper Trading の SQLite DB を解析して検証レポートを生成する CLI を追加。
  - 指標:
    - 稼働率（uptime_pct: system_status）
    - 注文関連（Created/Filled/Sent）からの注文成功率・送信率
    - リスク却下数（risk_logs）
    - レイテンシ（avg, max, P95）を trade_logs から算出
  - 合格基準（しきい値）を定義: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms。
  - CLI 引数 --from / --to / --db をサポート。デフォルト DB パスは data/paper_trading.db。
  - DB 欠落・テーブル未存在に対するフォールトトレランス（OperationalError を捕捉して N/A を扱う）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全スコアが 0 の場合は等配分へフォールバック。
  - risk_adjustment:
    - apply_sector_cap: 既存保有と予想エクスポージャーからセクター集中制限を適用（max_sector_pct による除外）。
      - unknown セクターは上限非適用。
      - 当日売却予定の銘柄をエクスポージャー計算から除外可能。
      - TODO コメント: 価格欠損時のフォールバック改善（将来対応予定）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（デフォルト 1.0、unknown は警告と共に 1.0）。
  - position_sizing:
    - calc_position_sizes: allocation_method により株数を算出（risk_based / equal / score）。
    - リスクベースの株数算出、単元株（lot_size）丸め、per-stock 上限 (max_position_pct)、aggregate cap（available_cash）に基づくスケーリング実装。
    - cost_buffer を考慮した保守的なコスト見積り、端数処理として lot 単位で再配分するロジックを実装。

- ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority: Windows / POSIX を吸収する優先度設定ユーティリティ。権限不足・未対応 OS は警告してスキップ。
  - set_cpu_affinity: カレントプロセスを最初の N コアにピンニング（例外処理とログ出力対応）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算。
    - 各関数はデータ不足時に None を扱う設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。有効レコード数が不足する場合は None を返す。
    - factor_summary / rank: 基本統計量算出・ランク計算。

- AI ニュース NLP (kabusys.ai.news_nlp) — 基盤機能
  - raw_news から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを算出する処理設計を実装。
  - 機能:
    - ニュース収集ウィンドウ計算（target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
    - 1銘柄あたり記事数・文字数上限（トークン肥大化対策）
    - バッチ送信（最大 20 銘柄／コール）、JSON Mode 出力の検証、スコアの ±1.0 クリップ
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ
    - OpenAI API キー必須（api_key 引数または環境変数 OPENAI_API_KEY）
  - 注: ファイルの末尾が切れているため、DB 書き込みの完全な実装や一部の詳細は未確認だが、設計・バリデーション方針は明確に記載。

Changed
- .env 読み込みの仕様を明確化:
  - OS 環境変数 > .env.local > .env の優先順位を採用し、.env.local は .env をオーバーライドする。
  - OS 環境変数を保護するため protected セットを用いて .env の上書きを制御。

Fixed
- 各モジュールでのエラー耐性を強化:
  - run_monitoring / run_execution のループ内で予期しない例外を捕捉してログ出力後に継続（監視が止まらないように）。
  - paper_verification_report でテーブル未存在時の sqlite3.OperationalError を扱い、レポート出力を続行可能に。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API を利用する機能では API キーを必須化（環境変数 OPENAI_API_KEY または明示的引数）。キー未設定時はエラーを明示。

Notes / Known limitations / TODOs
- sector exposure の計算で price が欠損（0.0）の場合にエクスポージャーが過少見積もられる点を TODO コメントで指摘。将来的な価格フォールバック実装を検討。
- DuckDB の executemany に関する互換性の注意（tools 内コメント）。
- ai/news_nlp.py の末尾が不完全であり、完全な DB 書き込み処理やエラーハンドリングの最終形は未確認。
- process_priority の設定は権限不足や未対応 OS ではスキップされるため、運用環境での権限確認が必要。

参考
- .env のパース仕様や各種デフォルト値、しきい値、ファイルパスはソース内ドキュメントコメントに従って決定されています。運用環境での挙動を変更するには該当の環境変数を設定してください。

--- 

今後のリリースでは、news_nlp の完成、価格フォールバック、テストケース拡充、ドキュメント整備（API 使用法・設定例）を優先することを推奨します。必要であればこの CHANGELOG をより細かいリリース単位（コミット単位）に分割して作成します。どの粒度で記載したいか指示ください。