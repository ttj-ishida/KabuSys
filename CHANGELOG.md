CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。
https://keepachangelog.com/ja/

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。日本株自動売買フレームワーク "KabuSys" の基礎機能を追加。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト。
      - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient による完全分離された検証実行をサポート。
      - 起動時にプロセス優先度を "high" に設定する仕組みを追加。
      - duckdb を併用して分析用・履歴用データにアクセス。
    - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視処理は本番用 sqlite_path を使用（環境に依存しない）。
      - 監視ループで例外を拾ってログ出力後に次のポーリングを継続するフェイルセーフを実装。
  - 設定管理
    - kabusys.config.Settings: 環境変数 / .env(.local) の自動読み込みとラップ。プロジェクトルートの自動検出（.git または pyproject.toml）による .env 自動ロードを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 各種パス・閾値・フラグをプロパティ経由で取得（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_ENV の検証（development/paper_trading/live）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルのスコアで上位 N 選定（タイブレーク: signal_rank）。
      - calc_equal_weights / calc_score_weights: 等比率・スコア加重の重み計算。全スコアが 0 の場合は等配分にフォールバックして警告。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価ベースでブロック）。"unknown" セクターは上限適用対象外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。未知レジームは 1.0 にフォールバック（警告）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株丸め、per-stock および aggregate 上限、cost_buffer を使った保守的見積もりとスケーリングロジックを実装。
      - aggregate cap のスケールダウンと端数処理（lot_size 単位で再配分）を実装。
      - TODO/注記として価格欠損時のフォールバック等を明記。
  - リサーチ / ファクター計算
    - research.factor_research
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB の prices_daily を参照）。
      - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比率を計算。
      - calc_value: EPS/ROE を用いた PER / ROE 計算（raw_financials と prices_daily を参照、target_date 以前の最新財務データを取得）。
    - research.feature_exploration
      - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得。
      - calc_ic / rank / factor_summary: IC（Spearman）計算、ランク付け、統計サマリーを実装。外部依存は排除（標準ライブラリのみ）。
  - AI ニュース NLP
    - ai.news_nlp
      - raw_news を銘柄ごとに集約し OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込み。
      - バッチ処理（最大 20 銘柄／API コール）、トークン肥大化対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
      - レスポンスの厳密な JSON バリデーションとスコアクリッピング（±1.0）。
      - API キーは引数または OPENAI_API_KEY 環境変数から解決。未設定時は ValueError。
      - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して使用。ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計。
  - 監視 DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を使用して起動時に監視用テーブル存在を冪等に保証。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority: Windows / POSIX を吸収して current process の優先度を設定。失敗時は警告でスキップ。
      - set_cpu_affinity: N コアへの固定をサポート（利用不可時は警告でスキップ）。
  - 運用ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト。
      - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計・表示。
      - 判定用閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
      - --from/--to/--db CLI 引数をサポート。PAPER_TRADING_SQLITE_PATH 環境変数も参照。
  - パッケージ基礎
    - パッケージバージョンを __version__ = "0.1.0" に設定。
    - research モジュールのエクスポート調整（zscore_normalize の導出を含む）。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Security
- 外部 API キーは環境変数経由での注入を想定。OpenAI キー未設定時は明示エラーを出す仕様。

Notes / Known issues / TODO
- position_sizing / risk_adjustment に price 欠損時のフォールバック（前日終値など）に関する TODO が残っています。
- news_nlp の大きな処理は部分的に失敗した場合でも既存スコアを保護するため、更新対象コードを絞って DELETE→INSERT を行う設計ですが、部分失敗時の運用手順をドキュメント化する必要があります。
- duckdb/SQLite のスキーマ変更やバージョン互換性については将来のマイグレーション機構が必要になる可能性があります。

問い合わせ / 貢献
- バグ報告・機能要望は issue を立ててください。README / ドキュメントに環境変数一覧や起動手順を追記する予定です。