# Changelog

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

- ルール: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - ロード順: OS環境変数 > .env.local > .env。OS環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは以下をサポート:
    - 行頭の `export KEY=...` 形式
    - シングル／ダブルクォート、バックスラッシュエスケープ
    - 行内コメント処理（クォートなしで `#` の直前がスペース/タブの場合はコメントとして認識）
  - 必須環境変数未設定時に明示的エラーを送出する `_require()` を提供。
  - 主要設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値, LOG_LEVEL, KABUSYS_ENV 等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。

- 実行ランナー / エンジン (kabusys.run_execution)
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite DB を使用し（data/paper_trading.db デフォルト）、本番 DB と完全分離して MockBrokerClient を利用する運用フローを想定。
  - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - 監視テーブル初期化（init_monitoring_db）を起動時に冪等に保証。
  - RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）および初期ポートフォリオ値に broker.get_available_cash() を利用。
  - Engine は PID ファイルパスを受け取りプロセス管理をサポート。

- 監視ランナー (kabusys.run_monitoring)
  - SystemMonitor ポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔の上書きが可能（デフォルト: 60 秒）。不正値 (0 以下 / 非数) はデフォルトにフォールバックし警告を出力。
  - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視は本番 DB を監視する想定）。
  - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証する処理を追加（冪等）。

- プロセス優先度・CPU affinity ユーティリティ (kabusys.utils.process_priority)
  - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する set_process_priority(level) を追加（high/normal/low）。
  - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加。
  - 権限不足や未サポート環境では警告を出してフォールバック。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選択。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア比率で配分。全銘柄スコアが 0 の場合は等金額配分へフォールバックし WARNING 出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を超える場合に新規候補を除外。売却予定銘柄をエクスポージャー計算から除外可能。unknown セクターは制限の対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返却（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックして警告を出力。
  - position_sizing:
    - calc_position_sizes: weight / candidates / portfolio_value / available_cash 等を基に銘柄ごとの発注株数を計算。
    - 対応する allocation_method: "risk_based", "equal", "score"。
    - 単元株 (lot_size) で丸め処理。per-stock 上限 (max_position_pct)、aggregate 上限 (available_cash) を考慮。
    - コストバッファ (cost_buffer) を考慮した保守的な見積りと、aggregate cap 超過時のスケールダウンアルゴリズム（端数扱いの再配分ロジックを含む）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を算出（DuckDB の prices_daily を利用）。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と prices_daily から PER / ROE を計算（target_date 以前の最新財務データを使用）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズン）を計算。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足時は None を返す。
    - factor_summary, rank: 基本統計量・ランク関数を提供。
  - DuckDB 接続を受け取り SQL + Python で処理、外部 API には依存しない設計。

- AI ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news / news_symbols を元に OpenAI (gpt-4o-mini) を用いて銘柄単位のセンチメント (-1.0〜1.0) を算出し ai_scores テーブルへ書き込むロジックを実装。
  - 処理フロー:
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC で算出）。
    - 1 銘柄あたりの記事数/文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄/バッチで API 呼び出し。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - レスポンス検証とスコアの ±1.0 クリップ。
    - 部分失敗時でも他銘柄スコアを保護するため、更新は対象コードに限定して置換的に実行。
  - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
  - 実装上の注意: DuckDB executemany の制約を考慮（params が空でないことを確認）。

- ツール: Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
  - CLI ツールとして paper trading の検証レポートを標準出力に生成。
  - 指標:
    - 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。
  - デフォルト DB パスは data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
  - パスが存在しない場合のエラーメッセージを出力。
  - 判定基準（PASS/FAIL）と閾値を定義:
    - 稼働率 >= 99%
    - 注文成功率 >= 90%
    - 送信率 >= 95%
    - P95 レイテンシ <= 200 ms
  - P95 計算、日付フィルタ、各種クエリ実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env 読み込みでファイルオープン失敗時に warnings.warn を出し安全にスキップするように実装（読み込み不能時の堅牢性向上）。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理と警告出力を追加（time.sleep に負の値を渡さないための予防）。

### 既知の制約・注意事項 (Notes)
- 多くのモジュールは外部 DB（SQLite / DuckDB）や外部 API（kabu API, OpenAI）に依存するため、本番稼働時は該当サービスの設定・環境変数の準備が必要。
- process_priority / cpu_affinity は OS 権限やプラットフォーム依存のため、動作しない場合は警告を出してスキップする。
- position_sizing の価格欠損（0.0）の場合、エクスポージャーや最大株数の過少見積りに繋がる旨の TODO 注記あり。将来的に前日終値等のフォールバックを検討する必要あり。
- news_nlp は OpenAI のレスポンスフォーマットや API 利用制限に依存。API 仕様変更やコストに注意。
- research モジュールは DuckDB 上の prices_daily / raw_financials スキーマに強く依存。

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

もし CHANGELOG に記載してほしい追加のポイント（例: 重点的に伝えたい設計決定、API の互換性、将来の TODO 優先度など）があれば教えてください。コードベースから推測できる範囲で追記します。