# Changelog

すべての重要なリリースノートはこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

現在の日付: 2026-04-11

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-11

初回公開リリース。以下の主要機能を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョン定義: kabusys.__version__ = "0.1.0"。

- 設定・環境変数管理
  - kabusys.config.Settings: 環境変数から設定を取得する一元化された設定クラスを追加。
  - 自動 .env 読み込み機能:
    - プロジェクトルートを .git または pyproject.toml から検出。
    - `.env` と `.env.local` の順序で読み込み（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサ実装: export 形式、クォート処理、インラインコメント処理に対応。
  - 各種設定プロパティを追加（DB パス、PID/KILL フラグ、しきい値、paper_trading 関連設定など）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。

- 実行用スクリプト
  - run_execution.py:
    - ExecutionEngine の起動処理。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使って本番 DB と分離（mock broker を利用する設計）。
    - ブローカークライアントファクトリ、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててセッション実行。
    - duckdb と sqlite の接続管理（open/close）。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に High に設定。

- 監視/実行ユーティリティ
  - kabusys.utils.process_priority:
    - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティ。
    - 権限不足や未対応環境では警告を出して安全にスキップ。
    - set_process_priority, set_cpu_affinity を提供。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: シグナルをスコア降順/同点タイブレークで選抜。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコア 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を防ぐための候補除外ロジック（売却予定銘柄を考慮）。
    - calc_regime_multiplier: market レジームに対する投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method に応じた株数決定（risk_based / equal / score）。
    - lot_size による丸め、per-stock 上限、aggregate cap（available_cash を超えた場合のスケールダウン）と端数配分ロジックを実装。
    - cost_buffer による手数料・スリッページ見積を考慮。

- リサーチ / ファクター計算（DuckDB ベース、外部依存最小化）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせ PER / ROE を算出。
    - 全関数は DuckDB 接続を受け取り SQL で集計。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（horizons の検証あり）。
    - calc_ic: ファクターと将来リターンのランク相関（スピアマン ρ）を計算。3 件未満は None。
    - rank / factor_summary: ランク計算（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）。
    - pandas など外部ライブラリ非依存で実装。

- AI 関連
  - kabusys.ai.news_nlp:
    - raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄別センチメントを算出し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを提供。
    - バッチ処理（最大 20 銘柄/コール）、記事トリム（最大記事数 / 文字数制限）実装。
    - API エラー（429/接続/タイムアウト/5xx）は指数バックオフでリトライ、その他はフェイルセーフによりスキップ。
    - レスポンスバリデーション（JSON モード + 復元処理、results 構造検証、コード照合、数値検証、スコアクリップ）。
    - DuckDB への冪等書き込み（部分失敗でも他コードの既存データを消さない DELETE → INSERT の処理）。
  - kabusys.ai.regime_detector:
    - ETF 1321 の ma200 乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して market_regime を判定。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出、必要に応じて LLM 呼び出し。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 判定値を clip してテーブルへ冪等書き込み。

- DB/監視補助
  - monitoring_db.init_monitoring_db の呼び出しを run 系スクリプトで行い、監視用テーブルの存在を保証（冪等）。

- OpenAI 呼び出しの抽象化
  - news_nlp._call_openai_api はテスト時にモック差し替えしやすく設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は明示的にエラーを投げて安全に停止。

### Notes / Known limitations / TODOs
- apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価等でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 現状 lot_size は全銘柄共通の想定。将来的に銘柄別 lot_map を受け取る拡張を予定。
- DuckDB executemany の空リストバインドに関する互換性対策が各所で入っている（互換性のための注意点）。
- datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）を遵守しているが、呼び出し側が正しい target_date を渡すことを仮定。
- OpenAI との連携は外部 API に依存するため、レート制限やネットワーク障害を考慮した実運用設定が必要。

---

以上が本コードベースに基づく初回の CHANGELOG（0.1.0）です。必要であればリリースノート文言の調整や、より細かなファイル/関数単位の変更履歴分割も対応します。