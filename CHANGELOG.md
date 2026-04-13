# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。目標は後からの差分把握を容易にすることです。

- 仕様: https://keepachangelog.com/ja/1.0.0/
- 日付はリリース日を表します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-13

初回リリース。以下の主要機能・モジュールを実装しました。

### Added
- 基本メタ情報
  - パッケージバージョン: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境変数 KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を High に設定（utils.process_priority を利用）。
    - monitoring DB の初期化（init_monitoring_db）および DuckDB 接続を行う。
    - 例外発生時はログを出力して次のポーリングへ継続、CTRL+C（KeyboardInterrupt）で graceful に終了。

  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用し、本番 DB と分離して MockBrokerClient（BrokerClientFactory により生成）を使用する想定。
    - 起動時にプロセス優先度を High に設定。
    - ExecutionEngine の組み立て（Broker, OrderRepository, OrderManager, RiskManager, Reconciler）と session 実行を行う。
    - RiskManager のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）、初期ポートフォリオ値は broker.get_available_cash() を利用。

- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
    - Settings クラスを提供し環境変数に基づく各種設定（DB パス、API トークン、PID/KILL フラグパス、閾値、環境種別等）を取得・検証。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の入力検証を実装。Paper Trading 用 DB パス設定も追加。

- ユーティリティ
  - utils/process_priority.py
    - カレントプロセスの優先度設定（Windows と POSIX の差分を吸収）。
    - set_process_priority(level) — "high"/"normal"/"low" をサポート。権限不足等は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスをピン。権限・未対応 OS は警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして候補抽出（同点は signal_rank で tiebreak）。
    - calc_equal_weights: 等金額配分を計算（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバック（WARNING ログ）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）。既存保有のエクスポージャ計算は price_map を利用。unknown セクターは除外しない挙動。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（WARNING）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method="risk_based" / "equal" / "score" をサポート。
    - risk_based: 損切り幅・許容リスク率から株数を算出。
    - equal/score: 重みから割当てを算出。単元株（lot_size）で丸め、per-position 上限と aggregate cap（available_cash）を考慮。
    - cost_buffer を考慮した保守的見積り、投資が available_cash を超える場合のスケールダウンと残差処理（lot 単位で追加配分）を実装。
    - price 欠損時はスキップする旨をログで出力。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン・200日移動平均乖離率（MA200）を計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR（true range ベース）、ATR 比率、20日平均売買代金・出来高比などを計算。NULL 値伝播に注意した実装。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算。

  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証あり。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを付与する実装（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

  - research/__init__.py エクスポートを整備。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメント解析を実行し、ai_scores テーブルに書き込む処理を実装。
    - ニュースウィンドウの算出（JST 基準の前日 15:00 ～ 当日 08:30 を UTC へ変換）を提供。
    - バッチ処理（最大 20 銘柄/コール）、スコアクリッピング（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ、上限回数あり）等を実装。
    - API キー未設定時は ValueError を送出。部分失敗に備え、DB 書き込みは影響範囲を限定する設計（既存スコア保護のためコード絞込みを行う）。
    - トークン肥大化対策として記事数・文字数の上限を設ける（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均・最大・P95）を算出し、閾値と比較して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、空データ時の振る舞い（N/A 表示）および CLI オプション（--from/--to/--db）を実装。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。

- その他
  - モジュールの __all__ とパッケージのインポートエクスポートを整理（portfolio, research, tools 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給する設計。未設定時は明示的にエラーを出すことで誤動作を抑止。

### Notes / Known limitations
- ai/news_nlp.py の処理は OpenAI API を使用するため、実行時にネットワーク/課金/レート制限の影響を受けます。部分失敗を想定しているものの、運用上の監視が必要です。
- portfolio.position_sizing: price_map（open_prices）に欠損がある場合、該当銘柄はスキップされます。将来的にフォールバック価格（前日終値等）を導入する余地があります（TODO コメントあり）。
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。配布後にルート検出が失敗した場合は自動ロードをスキップします。
- run_monitoring は monitoring 用 DB に常に本番 sqlite_path を使用します。Paper Trading と完全分離したい場合は起動スクリプト側で設定を変更してください。

---

発見した差分や追加してほしい詳細（例: リリースノートに含める各ファイルの実装上の制約や既知のバグ）などがあれば教えてください。必要に応じてセクションを分割・追記します。