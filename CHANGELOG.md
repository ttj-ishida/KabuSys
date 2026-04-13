# Changelog

すべての重要な変更点をここに記録します。フォーマットは Keep a Changelog に準拠しています。

注意: 以下の内容は提供されたコードベースの実装内容から推測して作成しています（実運用での挙動や追加の変更点はリポジトリの履歴と照合してください）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-13

Added
- 基本アプリケーション構成
  - パッケージのバージョンを定義: kabusys.__version__ = "0.1.0"
- 実行用エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）はデフォルトにフォールバックして警告を出す。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を利用）。
    - 監視用 DB（SQLite）と DuckDB 接続を確立し、監視テーブルの初期化を実行。
    - KeyboardInterrupt をハンドリングしてクリーンに終了。
    - 注意書き: Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite DB を使用して本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索し、OS 環境変数を保護）。
    - .env パーサーは export 付き行、クォート（シングル/ダブル）とバックスラッシュによるエスケープ、コメント扱いの微妙な仕様を処理。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスを実装し、各種環境変数をプロパティ化（検証ロジックを含む）。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject" の検証）
      - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, 閾値（CPU/MEMORY/DISK）など
      - KABUSYS_ENV の検証（development / paper_trading / live）
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows と POSIX 系を吸収）。
    - set_cpu_affinity(cpu_count) を実装（指定コア数にプロセスをピンニング）。
    - 権限不足や未対応プラットフォームの場合は警告ログを出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア総和が 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別時価を計算し、閾値超過セクターの候補を除外）。
    - 市場レジームに応じた資金乗数を返す calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは警告して 1.0 にフォールバック）。
    - 一部 TODO コメント（価格欠損時のフォールバック等）。
  - portfolio/position_sizing.py
    - リスクベース・等分配・スコア配分に基づく株数計算 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウンロジック、cost_buffer を考慮した保守的見積りを含む。
    - 将来的な拡張（銘柄別 lot_size のサポート）を想定したコメントあり。
- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算を実装（prices_daily / raw_financials を参照）。
    - momentum（1M/3M/6M、MA200 乖離）、volatility（ATR20、相対 ATR、出来高指標）、value（PER/ROE）を計算する関数を追加。
    - データ不足時に None を返す等の堅牢な取り扱い。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク化ユーティリティ (rank) を実装。
    - pandas 等の外部ライブラリに依存せず標準ライブラリで実装。
- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供（calc_news_window）。
    - バッチサイズ、最大記事数／文字数トリム、リトライ（429/5xx/ネットワーク/タイムアウトに対する指数バックオフ）等を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の保護（書き込みは対象コードで限定して差し替え）などのフェイルセーフ設計を採用。
    - OpenAI API キー未設定時は例外を送出して明示。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加（CLI）。
    - システム稼働率・注文成功率・送信率・P95 レイテンシ等を計算して PASS/FAIL を判定する閾値を定義。
    - SQLite（paper trading DB）を読み、対象期間フィルタリング（--from / --to / --db オプション）に対応。
    - SQL の存在チェックや OperationalError のフォールバック処理を実装。
- パッケージエクスポート
  - research/__init__.py、portfolio/__init__.py 等で主要関数を再エクスポートする形で公開 API を整理。

Changed
- なし（初回リリースとして新規実装の集合）

Fixed
- 環境変数パーサーの堅牢性向上
  - export プレフィックス、クォート内のバックスラッシュエスケープ、コメント判定の取り扱いを改善。
- exec/misc: DuckDB executemany に対する注意事項（空 params の防止）をコードコメントで明記。

Security
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）未設定時は ValueError を送出して早期に検出する実装を追加。

Known issues / Notes / TODO
- apply_sector_cap 内に price が欠損（0.0）の場合エクスポージャーが過少評価される可能性がある旨の TODO コメントがある。将来的に前日終値や取得原価でのフォールバックを検討すること。
- position_sizing は現状全銘柄共通の lot_size を想定。将来的に銘柄別 lot_map へ拡張予定（TODO コメントあり）。
- ai/news_nlp.py は外部 API 呼び出しを行うため、API 利用料・レート制限・キー管理に注意が必要。API のエラーやレスポンス仕様変更に備えたリトライ・検証ロジックはあるが、部分失敗時の運用手順を文書化することを推奨。
- run_monitoring の動作は KABUSYS_ENV に依存せず production sqlite_path を使用するため、テスト目的で監視を分離したい場合は運用上の注意が必要（別プロセスや設定で対応）。

追加された（または必要になった）環境変数（主なもの）
- KABUSYS_ENV (development | paper_trading | live)
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
- SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
- PAPER_FILL_MODE (instant | partial | never | reject)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（ai/news_nlp で必要）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env 読み込みを無効化するフラグ）

以上

--- 
（今後のリリースでは各コミットや PR 単位で変更を細かく分割し、Unreleased セクションに作業中の変更を追加してください。）