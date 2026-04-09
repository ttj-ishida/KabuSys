# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新の変更は上にあります。

## [Unreleased]

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買フレームワークのコア機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージのバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。
  - モジュールエクスポート定義（data, strategy, execution, monitoring 等）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / 環境変数からの自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）により CWD に依存しない読み込みを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサー実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理等に対応）。
  - 環境変数取得ヘルパーと必須チェック（_require）。
  - Settings クラス：J-Quants / kabuステーション / LINE / DB パス / Paper Trading 設定 / 監視値 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを提供。
  - env / log_level / PAPER_FILL_MODE 等のバリデーションを実装。無効値は ValueError を送出。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして候補抽出。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等重配分にフォールバックし WARNING を出力。
  - risk_adjustment
    - apply_sector_cap: 同一セクター集中を制限するフィルタ。既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数（デフォルトマップと未知レジームのフォールバック／警告処理）。
  - position_sizing
    - calc_position_sizes: 発注株数計算。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率（risk_pct）、損切り率（stop_loss_pct）に基づいて株数算出。
    - equal/score: 重み（weights）に基づく配分。per-position 上限・aggregate cap を考慮。
    - lot_size（単元株丸め）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）等に対応。
    - aggregate cap 超過時のスケーリング処理（スケールダウン→端数（lot 単位）再配分ロジック）を実装。
    - price 欠損時にスキップする安全処理と詳細なデバッグログ。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離（ma200_dev）を DuckDB の prices_daily から計算。ウィンドウ不足時は None を扱う。
    - calc_volatility: 20日 ATR / ATR 比率 / 20日平均売買代金 / 出来高比を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0 または欠損時は None）。
  - feature_exploration
    - calc_forward_returns: target_date から各ホライズン先のリターンを一括で計算（LEAD を使った効率的取得）。horizons 引数の検証あり。
    - calc_ic: スピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None。
    - rank: 同順位は平均ランクで処理（丸めによる ties 検出漏れ防止のため round を利用）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計（研究用に外部 API へはアクセスしない方針）。

- AI 機能（src/kabusys/ai）
  - news_nlp (score_news)
    - raw_news と news_symbols を基に指定時間ウィンドウのニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む。
    - タイムウィンドウ: target_date に対して前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で計算する calc_news_window を提供）。
    - 記事トリム（記事数・文字数制限）とバッチ処理（最大 BATCH_SIZE=20 銘柄／回）。
    - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx を対象）と指数バックオフ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score の検証、スコアの ±1.0 クリップ）。
    - DB 書き込みは部分成功考慮（対象コードのみ DELETE → INSERT）およびトランザクション制御（BEGIN/COMMIT/ROLLBACK）。
    - API キー解決: 引数 or 環境変数 OPENAI_API_KEY。未設定時は ValueError。
    - フェイルセーフ: API 失敗時はスキップして継続し、例外を上位に伝播させない（安全性重視）。テスト容易性のため _call_openai_api を差し替え可能。
  - regime_detector (score_regime)
    - ETF 1321 の ma200 乖離とマクロニュースの LLM センチメントを合成して daily market_regime を判定し DB に書き込む（冪等）。
    - ma200Ratio 計算は target_date 未満のデータのみを使用し、データ不足時は中立 (1.0) をフォールバックして警告を出力。
    - マクロキーワードで raw_news を抽出し、LLM でマクロセンチメントを評価。API 失敗時は macro_sentiment=0.0 で継続。
    - 合成スコアにより regime_label を bull / neutral / bear に分類。
    - トランザクション制御（BEGIN/DELETE/INSERT/COMMIT）とエラーハンドリング。
    - OpenAI 呼び出しロジックは news_nlp と独立実装（モジュール分離）。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 用の監視用テーブル群（system_status, trade_logs, positions, risk_logs など）とインデックスを冪等に作成するスクリプトを実装。

- モジュール再エクスポート
  - src/kabusys/portfolio/__init__.py / src/kabusys/research/__init__.py / src/kabusys/ai/__init__.py により主要関数をパッケージトップからインポート可能に。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known limitations / TODO
- position_sizing.calc_position_sizes:
  - 単元株数 lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map を受け取る設計拡張を予定（コード内 TODO）。
  - price が欠損（0.0）の場合にセクターエクスポージャーが過少見積りされる可能性がある旨の注記あり（将来的にフォールバック価格導入を検討）。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB で実装しているため、大規模データ処理時はパフォーマンス調整が必要になる可能性あり。
- AI 関連は外部 API 利用のため実行環境に OPENAI_API_KEY 等の設定が必要。テスト用に API 呼び出し部分は差し替え可能に設計。

---

開発／運用で上記以外に補足が必要な項目があればお知らせください。必要に応じて変更履歴を細分化して追記します。