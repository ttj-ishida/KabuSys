# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから内容を推測して作成しています（実装コメント・TODO・例外処理等を参照）。誤りや見落としがあればご指摘ください。

## [Unreleased]

### Known issues
- ai/news_nlp.py の実装が途中で切れている箇所があり（末尾で `if not articl` のような未完のコード）、そのままではモジュールが構文エラーまたは実行時エラーを起こします。OpenAI API 呼び出し周りの処理（記事集約、チャンク送信、レスポンス検証、DB書き込み）の完了が必要です。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される問題がある旨の TODO が残っています。前日終値などのフォールバック導入検討が必要です。
- portfolio/position_sizing:
  - 将来的に単元株数(lot_size) を銘柄別に扱う設計への拡張予定が記載されています（現状は全銘柄共通の lot_size 固定）。
- utils/process_priority.set_cpu_affinity:
  - cpu_count が利用可能コア数を超えた場合は全コアにフォールバックするが、期待した通りのピンニングにならないケースが出る可能性あり（ログ出力のみで対処）。権限不足時の警告は出るが代替動作がない。

---

## [0.1.0] - 2026-04-16

初回公開（推定）。以下はこのリリースで導入された主要な機能と実装内容の要約です。

### Added
- 全体
  - プロジェクト初期構成とバージョン管理（`kabusys.__version__ = "0.1.0"`）。
  - 環境設定読み込み・管理モジュール `kabusys.config.Settings` を追加。
    - .env/.env.local 自動読み込み（OS 環境変数優先）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 必須環境変数取得ヘルパ `_require()` と各種設定プロパティ（DBパス・APIトークン・閾値等）を実装。
    - `PAPER_FILL_MODE` の妥当性チェック（"instant" / "partial" / "never" / "reject"）。
    - 環境種別（development / paper_trading / live）とログレベルのバリデーション。
- 実行 / 監視
  - `run_execution.py` — ExecutionEngine 起動スクリプトを追加。
    - Paper Trading 環境では専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のスレッド実行・停止フラグ監視を実装。
    - Execution 用 PID ファイルパス / stop フラグ管理。
  - `run_monitoring.py` — SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（意図的な設計）。
    - stop フラグ検知でループ終了、例外はログ出力して次ポーリングへ継続。
  - 共通ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows/Linux/macOS でプロセス優先度（high/normal/low）を設定する `set_process_priority()`。
    - CPU アフィニティを設定する `set_cpu_affinity()`（権限不足や未対応環境時には警告を出してスキップ）。
- Portfolio（ポートフォリオ構築）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates()`（スコア降順・タイブレークロジック）。
    - 重み計算 `calc_equal_weights()`（等配分）、`calc_score_weights()`（スコア正規化、全スコア 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap()`（既存保有と当日売却予定を考慮して候補を除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier()`（"bull"/"neutral"/"bear" 対応、未知レジームはフォールバック 1.0）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック `calc_position_sizes()` を実装（allocation_method: risk_based / equal / score、aggregate cap スケーリング、lot_size 丸め、cost_buffer 加味）。
    - risk_based では stop_loss を用いた単一銘柄リスク計算、equal/score では重みベースの配分。
- Research（リサーチ）
  - `kabusys.research.factor_research`
    - Momentum / Volatility / Value 各ファクター計算（DuckDB を用いた SQL 実装）。
    - 結果は (date, code) 単位の dict リストで返却。
    - 実装ノートや窓幅（MA200, ATR20 等）・データ不足時の None ハンドリングを明記。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算 `calc_forward_returns()`（可変ホライズン対応、入力バリデーション）。
    - IC（Spearman ρ）計算 `calc_ic()`、ランク計算ユーティリティ `rank()`、ファクター統計サマリー `factor_summary()` を実装（外部ライブラリに依存しない純 Python）。
  - `kabusys.research.__init__` で主要関数を公開（zscore_normalize は kabusys.data.stats からエクスポート）。
- AI / ニュース
  - `kabusys.ai.news_nlp` にニュースセンチメントスコアリングの骨組みを追加。
    - ニュース収集ウィンドウ計算 `calc_news_window()`（JST→UTC の変換ロジック）。
    - OpenAI（gpt-4o-mini）を使ったバッチスコアリング設計（バッチサイズ、トークン肥大対策、リトライ/バックオフ、JSON Mode 想定、レスポンスバリデーション、±1.0 クリップ、部分成功時の DB 更新戦略等を仕様化）。
    - 実装は大半が整っているが（see Known issues）最終的な集約/書き込み部に未完の箇所あり。
- Tools
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを標準出力へ表示。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ 等。合格基準（閾値）と Pass/Fail 判定を出力。
    - P95 計算、日付フィルタング、DB 存在チェック、SQL の例外に対する堅牢なフォールバックを実装。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- .env パーサーの改善（`kabusys.config._parse_env_line`）
  - export 句のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、クォートなし値の '#' コメント処理の条件付検出などを実装し .env の解釈を堅牢化。
- 環境変数関連の安全措置
  - .env の自動ロード時に OS 環境変数を保護する protected set を導入（.env.local は override=True でも OS 環境変数を上書きしない）。

### Removed
- （該当なし）

### Security
- OpenAI API キーの扱いは明示（関数引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を投げる仕様とし、誤ったデフォルト漏洩を防止。

---

注記:
- モジュール間の DB 連携は sqlite3（監視・実行用）と DuckDB（リサーチ・AI 集計用）を併用する設計です。デフォルトファイルパスは Settings のプロパティで管理されます。
- Paper Trading を行う場合は `KABUSYS_ENV=paper_trading` を設定すると、実行スクリプトが paper 専用 DB を使うなどの分離を行います（監視は本番 DB を参照する仕様となっていますので運用時は注意してください）。
- 本 CHANGELOG はコード中のコメント・TODO・ログ記載内容から機能を推定して作成しています。正式なリリースノート作成時はコミット履歴やリリースタグに基づく精査を推奨します。