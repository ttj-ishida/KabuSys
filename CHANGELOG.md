# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

### Added
- 初期の開発中の改善点と小さな修正（次回リリースで反映予定）。
  - 一部の関数やユーティリティにログ出力や入出力検証を追加予定。
  - ドキュメント（コメント・docstring）の整備と注釈の拡張。

### Changed
- なし（次回のリリースでまとめて反映予定）。

### Fixed
- なし（次回のリリースでまとめて反映予定）。

---

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能・モジュールを含みます。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数/`.env` 読込と型検証の実装（自動ロードはプロジェクトルート検出に依存）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。OS環境変数の保護（protected）に対応。

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用 DB と mock ブローカーを使用可能（本番 DB と分離）。
    - 実行中のプロセス優先度を "high" に設定する処理を実行開始時に追加。
    - 停止フラグ（data/stop_requested.flag）で安全に停止できる仕組みを実装。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler の組み立てロジックを整備。
    - リスク設定 (RiskConfig) のデフォルトパラメータを定義（max_position_pct, max_utilization, rate_limit_per_sec 等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正な値は警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（モニタリング用 DB の初期化を保証）。
    - 停止フラグによるループ終了・例外発生時のログ出力と継続処理を実装。

- 設定・ユーティリティ
  - robust な .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱い等）。
  - Settings による各種プロパティを提供（DB パス、PID ファイル、閾値、環境判定メソッド等）。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証とエラーメッセージ整備。
  - utils/process_priority.py
    - プラットフォーム（Windows / POSIX 系）を吸収したプロセス優先度設定を提供。
    - CPU affinity を最初の N コアに固定するユーティリティを追加。
    - 権限不足や未サポート環境で警告を出して安全にスキップする実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークに signal_rank を使用）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックし WARNING 出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を時価で計算し上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。

  - portfolio/position_sizing.py
    - calc_position_sizes: リスクベース / 等配分 / スコア配分に基づく株数計算ロジック。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金でのスケールダウン）、cost_buffer による保守的見積りを実装。
    - 負荷や欠損価格時の安全なスキップ処理を追加。

- 研究（Research）モジュール
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily から計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を導入。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（対象日以前の最新財務データを選択）。

  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを LEAD を使って一括取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（ties は平均ランクで処理、十分なサンプル数がない場合は None を返す）。
    - factor_summary / rank: ファクターの基本統計量とランク化ユーティリティ。

  - research/__init__.py
    - 主要関数（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize を公開。

- AI ニュース NLP
  - ai/news_nlp.py
    - DuckDB 上の raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントをスコアリングして ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数と文字数のトリミング、JSON 出力フォーマット検証、スコアの ±1.0 クリップを導入。
    - 429・ネットワークエラー・5xx に対する指数バックオフ再試行ロジックを実装。
    - API キーの引数指定 or 環境変数 OPENAI_API_KEY 参照。未設定時は ValueError を送出。
    - ニュース集計ウィンドウ（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）を提供する calc_news_window。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から過去期間の検証レポートを生成する CLI スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出。
    - Pass/Fail の閾値（稼働率 99%、成功率 90% 等）を定義し、判定メッセージを出力。
    - DB が存在しない・テーブルが無い場合のフォールバック処理（N/A 表示）を実装。

### Changed
- 設計ポリシー
  - リサーチ・AI モジュールは本番口座・注文 API にアクセスせず、DuckDB / SQLite のローカルデータのみを参照する方針を明文化。
  - 日付/時刻処理で直接 datetime.today()/date.today() を参照しない実装（ルックアヘッドバイアス防止）。

- DB の扱い
  - 監視系（run_monitoring）は環境に関係なく本番 sqlite_path を参照する仕様を明確化。
  - paper_trading モード時は専用の paper_sqlite_path によって本番 DB と完全に分離する動作を実装。

### Fixed
- 入力検証とフォールバック
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合、警告を出してデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の不正値に対して明確な ValueError を投げるように実装。
  - calc_score_weights: 全スコアが 0.0 の場合、等金額配分へフォールバックし警告ログを出力。
  - factor_exploration.rank: ties（同順位）の扱いを平均ランクにしてスピアマン相関の精度を保つ。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

（注）本 CHANGELOG は現行コードベースの実装内容から推測して作成したものです。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。