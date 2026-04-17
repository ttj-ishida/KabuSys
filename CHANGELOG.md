# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 基本パッケージ情報
  - パッケージのバージョンを src/kabusys/__init__.py にて `0.1.0` として追加。
- 実行用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - 停止フラグ / PID ファイル管理、スレッドで ExecutionEngine を実行して安全に停止可能。
    - BrokerClientFactory を通じたブローカークライアント生成と依存コンポーネント組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
- 設定・環境管理
  - config.py: 環境変数・.env ファイルの自動読み込み機能を追加。
    - プロジェクトルートの検出（.git または pyproject.toml）に基づき .env/.env.local を読み込む。
    - .env パーサを実装（`export KEY=val`、クォート文字列、インラインコメント対応）。
    - OS 環境変数を保護して `.env.local` で上書き可能（上書き禁止リスト保護）。
    - Settings クラスを追加し、各種設定値（DB パス、API トークン、監視の閾値、環境種別判定メソッドなど）を提供。
    - `PAPER_FILL_MODE` や `KABUSYS_ENV`、`LOG_LEVEL` のバリデーションを実装。
- モニタリング関連
  - monitoring_db の初期化呼び出し（init_monitoring_db）を実行フローに組み込み、監視テーブルの存在を保証。
  - MONITOR_POLL_INTERVAL の入力バリデーション（0 以下や非数はデフォルトにフォールバックして警告ログ）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - コマンドライン引数で期間指定可能（--from, --to, --db）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - データが不足する場合は N/A をハンドリング。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（売却予定コードの除外対応、unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を算出（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: risk_based / equal / score に対応）。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）へのスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - スケールダウン時の残差分配ロジック（lot 単位で端数配分）を実装。
- 研究（Research）機能
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を用いたファクター計算を追加（モメンタム、ATR、流動性、PER/ROE 等）。
    - データ不足時は None を返す設計で安全に動作。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン計算（複数ホライズン、入力検証付き）。
    - calc_ic: スピアマンのランク相関（IC）計算（十分なサンプルがない場合は None を返す）。
    - rank / factor_summary: ランク付けと基本統計の算出（None 値除外、std/median 計算）。
  - research/__init__.py にユーティリティのエクスポートを追加。
- AI ニュース NLP
  - ai/news_nlp.py（ニュースのセンチメントスコアリング）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのスコアを ai_scores テーブルへ書込む想定。
    - API キーの解決、タイムウィンドウ（JST → UTC 変換）ロジック、バッチサイズ、トークン肥大化対策（記事数・文字数上限）、429/5xx/ネットワーク断に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗に対する局所的な DB 更新（該当コードのみ置換）など設計。
    - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を参照しない設計方針。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームに対応したプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）。
    - 権限不足や未サポート環境での例外を捕捉して警告ログでフォールバック。
  - 各モジュールの __init__ を整備してパブリック API を整理。

### Changed
- .env 読み込みの挙動
  - 自動読み込みの対象順序を明確化（OS 環境変数 > .env.local > .env）。
  - 環境変数読み込みをテスト等で無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を実装。
- DB ハンドリング
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用することを明示（監視用は本番 DB を参照）。
  - run_execution は paper_trading 環境向けに paper_sqlite_path を優先して使用するように変更（本番 DB と完全分離）。
- ログ・起動順
  - 実行スクリプトは起動時にプロセス優先度を最初に設定するように統一。
  - 各種初期化（init_monitoring_db、DuckDB 接続等）は起動フローで明示的に実行。
- バリデーション強化
  - MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL に対する入力検証とエラーメッセージを追加。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサで export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメントの取り扱いを正しく処理するように改善。
- 監視ループの安全性
  - check_once() 実行中に例外が発生してもループを継続し、例外時はスタックトレースをログに残して次ポーリングへ移行するように改善。
- ExecutionEngine の起動停止
  - 起動前に停止フラグを検知した場合はエンジンを起動しないように修正。
  - スレッド終了待機と停止命令送出のロジックを追加して安全に終了可能に。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨をコメントで記載。将来的に前日終値や取得原価などをフォールバック価格として利用することを検討中。
- ai/news_nlp.py:
  - 実装は堅牢化のため多くの安全策を備えているが、コード末尾が一部途切れている（推測される未完了箇所あり）。実際の API 呼び出し・DB 更新ルーチンの最終部分は別途完成が必要。
- 一部関数はデータ不足時に None を返す設計のため、呼び出し側での None ハンドリングが必要（レポート生成や上位ロジックで適切なフォールバックを行うこと）。

### Security
- OpenAI の API キーは明示的に引数 or 環境変数（OPENAI_API_KEY）から解決する設計で、未設定の場合は ValueError を発生させ処理を中止するようにしている（明示的な失敗で秘密情報漏洩防止）。

---

注: 上記はリポジトリのソースコードからの推測に基づいて作成した CHANGELOG です。実際のコミット履歴・リリースノートとは差異がある可能性があります。必要であれば、実際の git 履歴やリリース日を元に調整いたします。