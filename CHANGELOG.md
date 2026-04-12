# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
次の変更は重要な変更点のみを列挙しています。

注: リリース日には実装ファイルから推定した日付を使用しています。

## [0.1.0] - 2026-04-12

### Added
- 全体
  - 初回公開リリース。モジュール化された日本株自動売買ライブラリ/ツール群を追加。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV による paper_trading モードのサポート（paper_trading 用に専用 SQLite DB を使用し、本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
    - duckdb および sqlite 接続の確立とクリーンなクローズ処理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して DB 初期化を行う（init_monitoring_db）。
    - プロセス優先度を高く設定して起動（set_process_priority("high")）。
    - KeyboardInterrupt のハンドリングとリソースクリーンアップ。

- 設定 / 環境
  - config.py:
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で判定）。
    - OS 環境変数を保護するための上書きロジック（.env と .env.local の読み込み順と protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
    - .env パーサの強化（`export ` プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント取り扱い等）。
    - Settings クラス：多くの設定プロパティを追加（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、paper_trading 設定、監視閾値、PID/KILL フラグパス、環境判定など）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）。
    - LOG_LEVEL の妥当性チェック。

- ポートフォリオ構築
  - kabusys.portfolio:
    - portfolio_builder.py:
      - select_candidates: スコア降順・signal_rank によるタイブレークで候補選定。
      - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
    - position_sizing.py:
      - calc_position_sizes: risk_based / equal / score の配分方式をサポート。
      - 単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash）処理、cost_buffer を考慮したスケーリング処理を実装。
      - スケールダウン時の端数配分アルゴリズム（残差に基づく lot_size 単位での再配分）。
    - risk_adjustment.py:
      - apply_sector_cap: セクター集中上限に基づく候補除外（unknown セクターは除外しない）。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。

- リサーチ / ファクター計算
  - kabusys.research:
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
      - calc_volatility: ATR20、ATR 相対値、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials からの EPS/ROE を組み合わせた PER/ROE 計算（DuckDB）。
      - DuckDB を用いたウィンドウ関数・部分窓処理で欠損ハンドリング。
    - feature_exploration.py:
      - calc_forward_returns: 将来リターン（horizons）を一括で取得する SQL 実装。
      - calc_ic / rank / factor_summary: pandas 等に依存しない統計ユーティリティ（Spearman IC、ランク付け、基本統計量）。
    - research パッケージの __all__ エクスポートを整備（zscore_normalize を含む）。

- AI / ニュース NLP
  - kabusys.ai.news_nlp:
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
    - 処理概要:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
      - raw_news + news_symbols を銘柄別に集約（記事数・文字数上限によるトリム）。
      - 最大 20 銘柄/チャンクで API 呼び出し（JSON Mode 想定）、429/ネットワーク/5xx のリトライ（指数バックオフ）。
      - レスポンス検証、スコア ±1.0 にクリップ、ai_scores テーブルへの置換（部分失敗でも既存スコア保護のため code 絞り込みで DELETE→INSERT）。
    - score_news: APIキー引数または環境変数 OPENAI_API_KEY を使用。未設定の場合は ValueError。

- ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン実行可能: python -m kabusys.tools.paper_verification_report）。
    - 指標:
      - 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等。
      - デフォルトしきい値: 稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
    - DB パスは --db 引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
    - 各種クエリは存在しないテーブルに対して sqlite3.OperationalError を捕捉してフォールバック。

- ユーティリティ
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定。サポート外 OS は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定数の先頭コアに CPU affinity を設定するユーティリティを追加。
    - psutil での AccessDenied / NotImplemented を安全にハンドリングし警告ログを出力。

### Changed
- なし（初回リリースのため実装追加が中心）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

メモ / 注意点（実装から推測）
- 設定ファイルの自動ロードはプロジェクトルートの検出に依存するため、配布後や特殊な配置では無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）できる。
- paper_trading モードでは DB を完全分離する設計のため、本番データと干渉しない運用が可能。
- AI API 呼び出し部は外部サービス依存のため、キー管理・レート制限・コストに注意。
- position_sizing の lot_size 周りや price の欠損時の挙動については TODO コメントがあり、将来的な拡張余地がある。