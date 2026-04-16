# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-16
初回リリース。

### 追加
- 基本パッケージ情報
  - パッケージのバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として設定。

- 実行・監視用スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）の検出に基づいて安全に停止。
    - 実行中の PID を data/execution.pid に保存する仕組みを想定（pid_file の取り扱いをサポート）。
    - BrokerClientFactory を用いてブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskManager の初期設定値（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）をデフォルトで設定。

  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加（src/kabusys/run_monitoring.py）。
    - デフォルトポーリング間隔 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値はデフォルトにフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（monitoring データは常に本番 DB に記録）。
    - プロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）の検出でループを終了。
    - SQLite / DuckDB 接続の初期化およびクローズ処理を実装。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - 各種環境変数をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH 等）。
    - env の妥当性チェック（KABUSYS_ENV の有効値: development, paper_trading, live）およびログレベルの検証（LOG_LEVEL）。
    - PAPER_FILL_MODE の有効値チェック（instant, partial, never, reject）。
    - PID/kill flag に関するパス設定、閾値設定（CPU/MEM/DISK）など監視系設定を提供。
    - 環境変数自動読み込み: プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動読み込み（OS 環境変数は上書きされない）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中をチェックして候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投入資金乗数（bull/neutral/bear をマップし未知値は警告して 1.0 にフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）でのスケーリング、cost_buffer による保守的見積もり、残差処理による lot 単位の追加配分などを実装。
  - 上記モジュールをまとめたパッケージエクスポート（src/kabusys/portfolio/__init__.py）。

- 研究（Research）モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - momentum / volatility / value ファクター計算を DuckDB の SQL＋Python で実装（prices_daily / raw_financials を参照）。
    - 各種窓長やスキャン範囲を定数で管理。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、列の統計サマリ（count/mean/std/min/max/median）、ランク関数の実装。
    - pandas 等の外部ライブラリに依存せず純 Python 実装。
  - research パッケージのエクスポート（src/kabusys/research/__init__.py）で主要関数を公開。
  - DuckDB 接続を受け取る設計により、本番 API へはアクセスしないことを明確に設計。

- AI ニュース NLP
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む想定のモジュールを追加。
    - バッチ処理、トークン肥大化対策（記事数・文字数トリム）、エクスポネンシャルバックオフによる再試行、レスポンス検証、スコアのクリップ、部分失敗時に既存コードのスコアを保護する DB 操作設計を盛り込む。
    - OpenAI API キーの引数・環境変数参照（OPENAI_API_KEY）をサポート。未設定時は ValueError を送出。

- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 DB（デフォルト: data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計して検証レポートを標準出力に出力する CLI ツールを追加。
    - レポート出力では P95 計算、閾値（稼働率99%、成立率90%、送信率95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db コマンドライン引数をサポート。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil を使用）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を考慮したデフォルト値を用意。未対応 OS は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加。アクセス権限不足や未実装 API の場合は警告してスキップ。

### 変更
- 環境変数ロードの挙動
  - プロジェクトルートを .git または pyproject.toml から探索して `.env` / `.env.local` を自動ロードする仕組みを追加（ただし OS 環境変数は優先して保護）。自動ロードを無効にするためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。

- 監視用 DB の扱い
  - run_monitoring の実装により、監視データは KABUSYS_ENV に関係なく常に Settings.sqlite_path（本番 sqlite）へ接続して記録されることを明示。

### 修正
- 環境変数パースの堅牢化（src/kabusys/config.py）
  - .env のパーサは次をサポート/処理:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - 行内コメントの扱い（クォートの有無により挙動を制御）
  - 値検証に失敗した場合は ValueError を発生させ、ユーザーに分かりやすいメッセージを出力。

- MONITOR_POLL_INTERVAL の扱い（run_monitoring）
  - 環境変数値が不正（整数変換失敗や 1 未満）な場合はデフォルト（60 秒）へフォールバックして警告を出すように。

- DuckDB / SQLite 接続の初期化およびクリーンアップを try/finally で保護（スクリプト停止時にリソースリークを防止）。

### 注意 / 破壊的変更
- 環境変数自動読み込み
  - .env/.env.local の自動読み込みがデフォルトで有効になっているため、意図せずローカル .env が本番実行時に読み込まれる可能性があります。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 監視 DB の固定動作
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path に接続します。開発環境で監視情報を分離したい場合は sqlite_path を別のパスに設定してください。

- 環境変数の必須チェック
  - Settings の一部プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は未設定だと ValueError を送出します。デプロイ前に必要な環境変数を設定してください。

- OpenAI 依存
  - news_nlp は OpenAI API（gpt-4o-mini）を使用します。API キー未設定時は例外となるため、利用時は `OPENAI_API_KEY` の設定が必要です。

### セキュリティ
- 特にセキュリティ脆弱性に関する修正はこのリリースではありません。環境変数・APIキー等の管理は運用側で適切に行ってください。

---

今後の予定（例）
- ExecutionEngine / Monitoring の詳細なログ出力強化、Graceful shutdown の拡張。
- news_nlp のレスポンス処理完了部分（AI 呼び出し/DB 書き込みロジック）の実装完了とテスト追加。
- 単体テスト、統合テスト、CI ワークフローの整備。