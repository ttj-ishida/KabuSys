CHANGELOG
=========

この変更履歴は「Keep a Changelog」準拠の形式で、コードベースから推測して作成したものです。
日付は本ファイル作成日（2026-04-13）を使用しています。

フォーマット:
- Unreleased（開発中／未リリースの変更）
- リリース単位で Added/Changed/Fixed/Removed/Security を記載

Unreleased
----------
（なし）

[0.1.0] - 2026-04-13
-------------------

Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" の主要コンポーネントを追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須/任意環境変数取得。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）デフォルトを提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - 監視関連設定（PID ファイル、kill フラグ、しきい値等）。
    - KABUSYS_ENV の検証（development / paper_trading / live）とヘルパープロパティ is_live/is_paper/is_dev。
    - LOG_LEVEL の検証。

- 実行スクリプト
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告出力してデフォルトにフォールバック。
    - 監視用途では KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定する（utils/process_priority を利用）。
    - SQLite と DuckDB 接続を初期化し、SystemMonitor.check_once を定期実行。KeyboardInterrupt により安全終了。

  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db 等）を使用して本番 DB と分離。paper_trading 向けに MockBroker を使う設計（BrokerClientFactory 経由）。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine の依存コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立て、engine.run_session() を呼ぶ。
    - RiskManager のデフォルト構成（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定し、initial_portfolio_value を broker.get_available_cash() で取得。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを run_monitoring/run_execution に追加し、監視テーブルの存在を保証（冪等）。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プロセス優先度設定ユーティリティを追加（set_process_priority）。
  - Windows と POSIX(Linux/macOS/FreeBSD) を吸収する実装。psutil を利用して nice/priority を設定。権限不足等はログ警告でスキップ。
  - CPU affinity を設定する set_cpu_affinity を追加（必要コア数チェック・安全にスキップするフォールバックあり）。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額配分にフォールバックして警告ログ。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、既存保有のセクターエクスポージャが閾値を超えるセクターから新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告のうえ 1.0 にフォールバック。
  - position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を計算する主要ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベース方式では risk_pct と stop_loss_pct に基づきポジションを算出。等配方式では weights と max_utilization を利用。
    - 単元株（lot_size）単位で丸め、1銘柄上限、aggregate cap（利用可能現金 available_cash）を超える際のスケールダウンと端数の再配分ロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト計算をサポート。
    - 価格欠損時のスキップやログ出力を実装。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターンと 200日移動平均乖離率（ma200_dev）を計算。データ不足の場合は None を返す。
    - calc_volatility: 20日 ATR、ATR の相対値（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials から最新の財務データを参照して PER/ROE を計算。
    - DuckDB を利用し prices_daily や raw_financials テーブルのみを参照する設計。
  - feature_exploration.py:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）までの将来リターンを一括クエリで計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と基本統計量サマリを提供。
    - pandas 等外部ライブラリに依存せず標準ライブラリと DuckDB で実装。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を用いて OpenAI API（gpt-4o-mini）を使ったセンチメントスコアリング機能を追加。
  - スコアリングの処理フローを実装：
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC 変換で DB 検索）。
    - 記事を銘柄別に集約（1 銘柄につき最大記事数/文字数でトリム）。
    - 最大 20 銘柄ずつバッチ送信、429/ネットワーク/5xx に対して指数バックオフでリトライ。
    - レスポンス検証とスコア ±1.0 のクリップ。
    - 処理後は ai_scores テーブルへ対象コードのみを部分置換（DELETE→INSERT）することで部分失敗時の既存データ保護を実装。
  - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成スクリプトを追加。CLI オプション: --from, --to, --db。
  - PAPER_TRADING_SQLITE_PATH をデフォルト DB パスとして参照（または --db で上書き）。
  - 指標・閾値:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill rate) >= 90.0%
    - 送信率 (send rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - system_status / trade_logs / risk_logs テーブルから各指標を取得し、PASS/FAIL 判定を出力。データ欠損に対する耐性あり（テーブル未存在時は N/A や 0 で扱う）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で渡す仕様。自動で外部公開される挙動はなし。

Notes / Implementation details
- DB:
  - SQLite は監視・paper_trading 用、DuckDB はリサーチや時系列集計用に併用する設計。
  - init_monitoring_db() により監視テーブルの存在を担保する（冪等）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、実行系は本番 DB と完全に分離して data/paper_trading.db（デフォルト）を使用する。
  - PAPER_FILL_MODE によるモック約定挙動をサポート（instant/partial/never/reject）。
- フェイルセーフ:
  - 多くの外部操作（プロセス優先度変更、CPU affinity、外部 API 呼び出し）が失敗した場合でもログ出力して処理を継続する実装になっている。
- 設定検証:
  - Settings 側で多くの環境変数の妥当性チェックを行い、不正な値は ValueError を発生させる。
- 実行上の注意:
  - run_monitoring/run_execution は main 関数を持ち、スクリプト単独起動可能（__main__ ブロックあり）。
  - run_monitoring は MONITOR_POLL_INTERVAL の 0/負数を許容せず、範囲外はデフォルトにフォールバックする。

今後の提案（開発上の注意点）
- position_sizing の price 欠損時のフォールバック戦略（前日終値や取得原価）を実装すると、価格データ欠損による過少見積りを防げる旨が TODO コメントにあるため対応検討推奨。
- ai/news_nlp の結果の永続化に関するトランザクション／部分コミット戦略のテスト追加。
- .env パーサは多くのケースをカバーしているが、特殊ケースの追加ユニットテストを整備すると保守性が向上。

--- 
End of CHANGELOG.md