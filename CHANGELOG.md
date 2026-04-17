# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載します。  
以下は提供されたコードベースの内容から推測して作成した初期リリースの変更履歴です（ファイル中のコメントや実装から機能・制約・既知の問題点を抽出しています）。

フォーマット: https://keepachangelog.com/ja/ に準拠

## [0.1.0] - 2026-04-17
初回リリース（コードベースから推定した主要機能をまとめています）。

### Added
- 基本アプリケーション情報
  - パッケージバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git / pyproject.toml から検出）を実装。OS 環境変数を保護するための上書き制御あり。
  - 高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 各種設定アクセス用プロパティを提供：J-Quants / kabu API トークン、LINE 設定、DuckDB/SQLite パス、paper trading 用パス、監視閾値、環境モード判定（development/paper_trading/live）など。
  - 設定値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の有効値チェック）。
- 実行系スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使い本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 実行中は停止フラグファイル（data/stop_requested.flag）を監視して安全停止。
    - 実行中の PID を data/execution.pid に管理。
    - プロセス優先度を起動時に "high" に設定。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
- 監視系スクリプト
  - システム監視ポーリングループの起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検出でループ終了。
    - プロセス優先度を起動時に "high" に設定。
- 監視 DB 初期化ユーティリティ（import により利用）
  - monitoring_db 初期化呼び出し（存在しないテーブルを作成する冪等処理が想定されている）。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを提供（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, macOS, FreeBSD）を吸収する抽象 API（set_process_priority, set_cpu_affinity）。
    - 権限不足や未対応 OS 時は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークルール）
    - calc_equal_weights, calc_score_weights（スコア 0.0 の場合は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率に基づく新規候補の除外。unknown セクターは除外対象外）
    - calc_regime_multiplier（bull/neutral/bear 用乗数、未知レジームは 1.0 でフォールバック）
  - 株数計算（src/kabusys/portfolio/position_sizing.py）
    - リスクベース / equal / score に基づく発注株数計算
    - 単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer に基づく aggregate cap 調整
    - 端数の追加割当てロジック（fractional remainder に基づく優先配分）
  - エクスポージャ超過時のログ出力や価格欠損時のスキップなど堅牢な挙動
- 研究（research）モジュール（DuckDB ベース、外部 API へ依存しない）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER, ROE を raw_financials と価格から計算）
    - パフォーマンスを意識した SQL 実装、データ不足時は None を返す設計
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（将来リターンを一度のクエリで取得、horizons 検証あり）
    - calc_ic（スピアマンのランク相関で IC を計算。有効レコード 3 未満で None）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランクで処理）
  - research パッケージの __all__ を整備して外部利用を容易にしている
- ニュース NLP スコアリング（AI）機能（src/kabusys/ai/news_nlp.py）
  - raw_news から銘柄別に記事を集約し OpenAI (gpt-4o-mini) を用いてセンチメントを -1.0〜1.0 で評価し ai_scores テーブルへ書き込む設計。
  - バッチ処理（最大 20 銘柄 / コール）、トークン肥大化対策（記事数上限・文字数上限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）などの堅牢化方針を実装。
  - レスポンス検証、スコアの ±1.0 クリップ、部分更新（成功したコードのみ置換）により部分失敗への耐性を確保。
- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - CLI で SQLite（paper trading DB）から検証レポートを生成（期間指定 --from / --to、--db）。
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
  - P95 計算、SQL の存在エラーハンドリング、見やすいフォーマットで結果を標準出力に出力。

### Changed
- 環境読み込みの挙動を整理
  - OS 環境変数が優先されるロード順を採用（.env の後に .env.local を上書き読み込み）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
- 起動時にプロセス優先度を「高」にするポリシーを採用（監視 / 実行スクリプト共通）。
- DuckDB / SQLite の混在利用を前提とした設計に統一（研究処理は DuckDB、監視/実行は SQLite + DuckDB）。

### Fixed
- .env パーサのさまざまな corner-case（export プレフィックス、クォート内エスケープ、インラインコメントの扱い）に対応して安定化。
- calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックする処理を追加（警告ログあり）。
- calc_position_sizes: 単元株（lot_size）への丸め、aggregate cap 超過時の縮小ロジックを実装してオーダー資金超過を防止。

### Known issues / Notes
- ai/news_nlp.py は設計が詳細に記述されているが、提供されたソースの末尾が途中で切れており内部関数（例: _fetch_articles）の実装や一部ロジックが欠落しているように見えます。現状ではモジュールは未完成であり、実行時に NameError / SyntaxError などを発生する可能性があります。AI スコアリング機能を利用する場合は未実装部分の補完が必要です。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠落している（0.0）場合、エクスポージャが過小見積りされ想定外に候補が許容される恐れあり。コード内に TODO があり、将来的に前日終値や取得原価などのフォールバック価格を検討する必要あり。
- DuckDB の executemany に関する注記あり（ニュース NLP での使用における注意）。空パラメータでの実行を避けるなどの防御的実装が必要。
- process_priority の設定は権限やプラットフォームに依存し、AccessDenied/NotImplemented などで実行環境によりスキップされる場合がある（その場合は警告ログにより通知される）。
- run_monitoring の MONITOR_POLL_INTERVAL は環境変数で上書き可能だが、不正値（非数値・0以下）の場合はデフォルトにフォールバックするようになっている。

### Security
- OpenAI API キーや各種秘密情報は環境変数を通じて取得する設計。Settings._require による必須チェックがあり、未設定時は起動時に例外で通知される。
- .env 自動ロードは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

注:
- 上記の CHANGELOG は提供されたソースコードおよびファイル内のコメントから推測して作成しています。実際のコミット履歴や意図と差異がある場合があります。特に AI 関連モジュールの未完成部分や TODO コメントはそのまま反映しています。実際のリリース用 CHANGELOG として利用する場合は、各機能担当者によるレビューと補足（未実装箇所の対応履歴、セキュリティレビュー結果、テスト状況など）を推奨します。