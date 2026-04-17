# CHANGELOG

すべての注目すべき変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-17
最初の公開リリース。自動売買システムのコア機能群（設定管理、実行・監視用スクリプト、ポートフォリオ構成、ポジションサイジング、リスク制御、リサーチユーティリティ、Paper Trading 検証ツール、ニュース NLP 下位実装など）を実装。

### Added
- 基本パッケージ情報
  - `kabusys.__init__` にバージョン `0.1.0` を追加。

- 設定・環境変数管理
  - `kabusys.config.Settings` クラスを実装。複数の環境変数（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境フラグ 等）をプロパティ経由で取得可能。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装（`.env` → `.env.local`、OS 環境変数を保護して読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
  - `.env` パーサを堅牢化：`export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 各種入力値検証を追加（例: `KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` の有効値チェック）。未設定の必須キー取得時は例外を送出する `_require()` を用意。

- 実行エンジン起動スクリプト
  - `run_execution.py` を実装。プロセス優先度を設定して（`kabusys.utils.process_priority.set_process_priority("high")`）実行環境を初期化。
  - Paper Trading モード対応:
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - Broker クライアント生成を抽象化する `BrokerClientFactory`（実行時に Mock/実ブローカを切替）。
  - エンジンの依存コンポーネント組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
  - `RiskConfig` のデフォルト設定を用意（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値はブローカーの利用可能現金から取得。
  - 停止フラグファイル（`data/stop_requested.flag`）を監視し、存在時はエンジンを起動せず終了または実行中は停止処理を行う。PID ファイル管理をサポート。
  - DuckDB を分析用に接続。

- 監視（Monitoring）起動スクリプト
  - `run_monitoring.py` を実装。プロセス優先度を設定し、SystemMonitor を初期化してポーリングループを実行。
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトへフォールバック。
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（冪等な `init_monitoring_db` 呼び出し）。
  - 停止フラグ存在でループを終了。KeyboardInterrupt をハンドルしてクリーンに終了。

- Paper Trading 検証レポートツール
  - `kabusys.tools.paper_verification_report` を実装。CLI (`--from`, `--to`, `--db`) により指定期間の検証レポートを生成。
  - 指標・閾値（稼働率、注文成功率、送信率、P95 レイテンシ等）を定義し、system_status/trade_logs/risk_logs から統計を集計して PASS/FAIL を判定。
  - P95 計算、各種フォーマットユーティリティを実装。DB が存在しない場合のメッセージを出力。

- ポートフォリオ構築関連（純関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合に等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター比率が上限を超える場合、新規候補を除外。`unknown` セクターは除外対象外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（"bull":1.0, "neutral":0.7, "bear":0.3。未知レジームは警告の上で 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 各種配分方式（`risk_based`, `equal`, `score`）に対応した株数計算 `calc_position_sizes` を実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング（コストバッファ考慮）を実装。
    - スケーリング時の端数処理と残余キャッシュを用いた追加配分ロジックを備える。
    - 価格欠損時のスキップや logging により頑健化。

- リサーチ機能（DuckDB ベース）
  - `kabusys.research.factor_research`:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）`calc_momentum`。
    - ボラティリティ/流動性（ATR20、相対 ATR、20日平均売買代金、出来高比）`calc_volatility`。
    - バリュー（PER, ROE）`calc_value`（`raw_financials` から最新財務を取得して計算）。
    - DuckDB SQL を用いた効率的なウィンドウ集計実装。データ不足時は None を返す扱い。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算 `calc_forward_returns`（複数ホライズンをまとめて取得、入力検証あり）。
    - スピアマンのランク相関による IC 計算 `calc_ic`（データ不足や定数分散時は None）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸め誤差対策あり）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - `kabusys.research.__init__` に主要 API を公開。

- ニュース NLP（AI スコアリング）下位実装
  - `kabusys.ai.news_nlp` にニュース集約／OpenAI 呼び出しベースのスコアリングロジックを実装。
  - OpenAI モデル（デフォルト gpt-4o-mini）を用いて銘柄ごとのセンチメントを JSON 形式で取得、スコアを ±1.0 にクリップして `ai_scores` テーブルに置換する方針を実装。
  - 処理の設計上の注意：
    - タイムウィンドウ（JST 基準）計算ユーティリティ `calc_news_window` を実装。
    - バッチサイズ、記事文字数上限、最大記事数などのトークン肥大化対策を考慮。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、部分成功時の既存スコア保護（コード絞込みによる更新）等を予定。
  - 注意: ファイル末尾で処理が途中で切れている箇所があり（コード断片あり）、一部処理が未完であることを明記。

- ユーティリティ
  - `kabusys.utils.process_priority`:
    - Windows/Linux/Mac を吸収するプロセス優先度設定 `set_process_priority(level)` 実装（`high|normal|low`）。
    - CPU affinity 固定 `set_cpu_affinity(cpu_count)` を実装（権限・非対応プラットフォーム時は警告してスキップ）。
    - psutil の権限拒否や非実装例外を考慮して安全に降順を選択。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境ファイルの読み込みでのエッジケース（クォートやエスケープ、インラインコメント）に対応するパーサ実装により、誤読や不正入力時の挙動を改善。
- ポジションサイジングでの合計投資額が available_cash を超えた場合のスケールダウン処理と端数処理により、過大な発注を防止。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー取得は明示的に `api_key` 引数または環境変数 `OPENAI_API_KEY` を要求。未設定時は ValueError を送出して安全な失敗を行う設計。

---

注意事項 / 今後の改善候補（コードからの推測）
- `kabusys.ai.news_nlp` の処理が途中で終わっている箇所が見られるため、バッチ送信→レスポンス処理→DB 書き込みのフルパスが未完。例外処理や部分失敗時のロールバック戦略の確認が必要。
- `position_sizing` の価格欠損（price==0）の場合の挙動について TODO コメントあり（前日終値や取得原価のフォールバックを検討）。
- 将来的に lot_size を銘柄別に扱うための拡張（stocks マスタからの lot_map）が計画されている。
- Process priority / affinity 設定は権限やプラットフォーム依存で失敗することがあるため、運用環境での動作検証を推奨。

もし CHANGELOG に追加したい別の観点（既知の既定値一覧、運用手順、未実装タスク一覧など）があればお知らせください。