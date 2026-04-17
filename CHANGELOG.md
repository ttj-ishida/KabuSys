# CHANGELOG

すべての変更は Keep a Changelog の規約に準拠して記載しています。  
フォーマットは「種類別見出し (Added / Changed / Fixed / Removed / Security)」で整理しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

最初の公開リリース。自動売買システムのコア機能群（実行エンジン起動スクリプト、監視、設定管理、ポートフォリオ構築、リサーチ、ユーティリティ、Paper Trading 用検証ツール、ニュースNLP スコアリングの基盤）を追加。

### Added
- 全体
  - パッケージ基本情報を追加（kabusys.__version__ = 0.1.0）。
  - DuckDB / SQLite を用いるデータ基盤を前提とした各種モジュールを追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV により paper_trading モードを分離（paper_trading 時は paper_sqlite_path を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、別スレッドで engine.run_session を実行。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止。実行 PID を data/execution.pid に記録する想定（pid_file を受け取る設計）。
    - RiskManager のデフォルト設定値を明示（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) を検知してループ終了。check_once 呼び出し時の例外を捕捉して継続するフェイルセーフ。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数に基づく設定参照を簡易化。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local の読み込みルールを実装（.env.local が優先、OS 環境変数は保護）。
    - .env パーサーを強化：export KEY=val 形式、クォート値のエスケープ処理、インラインコメント処理などに対応。
    - 各種設定プロパティを追加（duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk thresholds, env/log_level 判定など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - settings 変数（モジュールレベル）をエクスポート。

- ポートフォリオ関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選出（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有エクスポージャーに基づき候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知値は警告を出して 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数計算（risk_based / equal / score の allocation_method をサポート）。
    - 単元株丸め（lot_size 単位）、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を含めた保守的コスト見積もり、残差分の lot 単位再配分ロジックを実装。
  - portfolio パッケージ __all__ エクスポートを整備。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務指標を取得して PER/ROE を計算。
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照する純粋関数として実装。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21]）を一括取得。
    - calc_ic: スピアマン（ランク）相関による IC 計算（小規模データや分散ゼロを適切にハンドリング）。
    - rank / factor_summary: ランク算出（同順位は平均ランク）、基本統計量（count, mean, std, min, max, median）を実装。
  - research パッケージのエクスポートを整備（zscore_normalize を data.stats から再エクスポート）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成 CLI を追加。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), P95 レイテンシ 等を計算して PASS/FAIL 判定を表示。
    - デフォルト DB: data/paper_trading.db、コマンドライン引数 (--from, --to, --db) に対応。
    - 指標閾値は定数化（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）。
    - DB のテーブル不足や OperationalError を穏やかに扱うフォールバックを実装。

- AI / ニュース NLP（基盤）
  - ai.news_nlp
    - raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄ごとにセンチメントをスコアリングするフローを実装。
    - バッチ処理（最大 20 銘柄/コール）、JSON Mode を期待したレスポンス、429/ネットワーク/5xx に対する指数バックオフリトライ、スコア ±1.0 でクリップ、部分成功時の DB 更新保護（対象コードのみ置換）などの設計を導入。
    - calc_news_window: Target date に対応するニュース取得ウィンドウ（JST→UTC 変換）を実装。
    - score_news: API キー解決・ウィンドウ計算・記事集約・API 呼び出し・応答バリデーション・DB 書込の責務を持つ想定。
    - 注意: ファイル末尾が途中で切れているため一部実装（記事集約フェーズ以降）が未完です（本 changelog の段階では「NLP 基盤の追加」 として記載）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows (psutil.HIGH_PRIORITY_CLASS 等) と POSIX (nice 値) を吸収してプロセス優先度を設定するユーティリティを追加。対応しない OS や権限不足は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を固定する関数を追加（引数検証・権限エラーのハンドリングあり）。
  - utils パッケージ初期化ファイル追加。

### Changed
- モジュール化 / API 設計
  - 各機能は外部依存（DuckDB 接続、SQLite コネクション、broker クライアント、ExecutionEngine 等）をコンストラクタ / 関数引数として受け取るように設計され、テスト可能性を考慮。
  - run_monitoring/run_execution は起動時にプロセス優先度を高に設定するよう変更（自動で set_process_priority("high") を呼び出す）。

### Fixed
- ロバスト性向上
  - .env 読み込みでファイルが開けない場合に warnings.warn を発生させつつ続行するように改善。
  - run_monitoring において MONITOR_POLL_INTERVAL の不正値を検出しフォールバックするバリデーションを実装（負値や非整数は警告してデフォルト 60 秒に戻す）。
  - 複数のクエリーで NULL やデータ不足時の安全な扱い（例: factor_research の ma200 カウントチェックや volatility の true_range NULL 伝播制御、paper_verification_report の sqlite3.OperationalError フォールバック）を追加。

### Removed
- （なし）

### Security
- OpenAI API キー取り扱いに関して score_news は明示的に引数 api_key または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を送出して安全性を保つ。

### Notes / Known issues
- ai/news_nlp.py が途中で切れており、記事取得（_fetch_articles）以降の処理が未完となっています。NLP のバッチ送信・レスポンス処理・DB 書込は設計済みですが、現状ではまだ実行フローが完結していないため本機能を利用する際は該当モジュールの完成が必要です。
- 各モジュールは DuckDB/SQLite、psutil、openai 等の外部パッケージに依存します。実行環境に応じたインストールが必要です。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）を用いてプロセス制御を行います。運用時はフラグファイルの作成・削除ポリシーに注意してください。
- position_sizing の lot_size は現行実装でグローバル固定（引数により変更可）。将来的に銘柄別単元対応（lot_map）を検討する旨コメントあり。

---

もしこの CHANGELOG を特定のリリース戦略（セマンティックバージョニング、リリース日付、Unreleased ブランチ）に合わせて調整したい場合や、各変更項目をさらに細かいチケット/コミットに紐付けて出力したい場合はお知らせください。