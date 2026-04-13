CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
コードベースの内容から推測して作成したため、実装意図やデフォルト値等を説明的に補っています。

Unreleased
----------

- （なし）このファイルは初期リリースの内容を基に作成しています。

0.1.0 - 2026-04-13
-----------------

Added
- 基本パッケージ情報
  - パッケージ名: KabuSys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - __all__ で主要モジュールを公開（data, strategy, execution, monitoring）。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定（デフォルト "high"）。
    - KABUSYS_ENV によって paper_trading 用 DB を分離（settings.is_paper を参照）。paper_trading 環境では MockBrokerClient を使用する想定（BrokerClientFactory 経由）。
    - SQLite（本番/専用 paper_trading）と DuckDB を接続して利用。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッションを実行。
    - リソースは finally ブロックで確実にクローズ。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0以下や不正値はデフォルトにフォールバックして警告出力。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。SystemMonitor.check_once() を例外捕捉しつつループ実行、KeyboardInterrupt をハンドルして安全終了。

- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）して .env, .env.local を自動ロード（OS 環境変数優先、.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば自動ロードを無効化可能。
    - 独自の .env パーサを実装（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理等）。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、PID/kill flag パス、閾値、環境判定等）。
    - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の許容値チェック、未設定の必須変数は例外）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選択。score の同点は signal_rank でブレーク。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分。全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有時価を基に除外判定）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投入資金乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight / equal / score / risk_based に応じた発注株数算出ロジック。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケーリング、cost_buffer を用いた保守的見積り、スケールダウン後の余剰配分ロジック（残差順）を実装。
    - データ欠損（価格が 0/None）等のケースでスキップしログ出力。

- 研究・ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily から計算。必要行数不足時は None を返す。
    - calc_volatility: ATR(20) / atr_pct / avg_turnover / volume_ratio 等を計算。true_range の NULL 伝播制御や行数チェック実装。
    - calc_value: raw_financials から最終財務データを取得し PER/ROE を計算（prices_daily と結合）。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD を用いる）を一括取得。horizons の検証（1〜252）を実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）で None を返す。
    - rank / factor_summary: ランク（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
  - research/__init__.py で主要関数と zscore_normalize をエクスポート。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI API (gpt-4o-mini) を用いて銘柄毎にセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数最大 10 件、文字数上限 3000/銘柄）を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数的バックオフ（最大リトライ回数 3）を実装。
    - 書き込みは対象コードを絞って置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）することで部分失敗時のデータ保護を実現。
    - OpenAI API キーの解決方法（引数優先、環境変数 OPENAI_API_KEY）と未設定時のエラーを実装。
    - 時間ウィンドウ計算: target_date に対して JST ベースの「前日 15:00 ～ 当日 08:30」を UTC に変換して使用。内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX 系（Linux/Darwin/FreeBSD）を吸収して優先度をセット。未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定。無効時・権限不足などは警告でスキップ。
    - AccessDenied 等の例外を捕捉して安全にフォールバックするログ出力。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 検証指標: 稼働率 (uptime), 注文成功率 (fill_rate), 送信率 (send_rate), レイテンシ (P95) 等を算出。
    - パス/閾値のデフォルトと CLI オプション (--from, --to, --db) を提供。
    - P95 計算ユーティリティ、SQL を用いた各種集計クエリ、欠損時の N/A 表示、Pass/Fail 判定の出力を実装。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。

Changed
- 設定・起動の設計に関する注意点（ドキュメント的変更）
  - 監視プロセスは環境に依存せず本番 sqlite_path を使用することを明示（run_monitoring.py の docstring）。
  - Paper Trading 実行は本番 DB と完全分離される（run_execution.py の docstring に明示）。

Fixed / Robustness improvements
- .env パーサの挙動を改善
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントルール（非クォートでは直前がスペース/タブの場合に # をコメントと解釈）に対応し、現実的な .env フォーマットへの互換性を向上。
  - .env の読み込みに失敗した場合は warnings.warn で穏やかに通知して続行。
- 各計算処理での欠損データ耐性
  - ファクター計算や position sizing、apply_sector_cap 等で入力データが不足する場合に None や空結果を返すことで安全にフォールバック。ログで詳細を出力。
- OpenAI 呼び出しのフェイルセーフ
  - API 呼び出しで失敗した場合にリトライやスキップを行い、部分失敗でも他処理を継続する設計。

Notes / Known limitations / TODO
- position_sizing.calc_position_sizes の価格欠損（price == 0.0）時の挙動に関する注意:
  - apply_sector_cap のコメントにもあるように price が欠損するとエクスポージャーが過少評価されて除外が外れる可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する旨をコメントで記載。
- AI モジュールは OpenAI API の応答フォーマットに厳密に依存するため、API 仕様変更時の影響が想定される。
- DuckDB の executemany に関する挙動（空パラメータは送らない等）に注意する設計が一部に存在。

References
- 環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - KABUSYS_ENV (development|paper_trading|live)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU/MEM/DISK 閾値 (CPU_THRESHOLD_PCT 等)
  - OPENAI_API_KEY（ai/news_nlp）

この CHANGELOG はコードベースの内容から推測してまとめたものであり、実際のコミット履歴とは異なる可能性があります。詳細な変更履歴を正確に反映するには Git のコミットログ等を参照してください。