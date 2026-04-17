# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/) の形式に準拠しています。  
日付はコードベースの現在状態（リリース候補）に基づいています。

## [0.1.0] - 2026-04-17

初回公開リリース。KabuSys のコア機能群を実装しました（設定読み込み、監視・実行ランナー、ポートフォリオ構築、ポジションサイズ計算、リサーチ/ファクター計算、ニュース NLP スコアリング、ユーティリティ等）。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - プロジェクトレイアウトと各種サブパッケージを追加（data, strategy, execution, monitoring, portfolio, research, ai, tools, utils）。

- 設定管理（kabusys.config）
  - Settings クラスを追加。環境変数から各種設定を取得するインターフェイスを提供（DB パス、API トークン、KABUSYS_ENV、ログレベル、監視閾値 など）。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を優先順に読み込む）。OS 環境変数は保護され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパース強化：export 形式のサポート、クォート／エスケープの取り扱い、インラインコメント処理など。
  - 環境変数の妥当性検証を実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 監視（run_monitoring, monitoring モジュール連携）
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループを起動するエントリポイント。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。不正な値はログ警告の上デフォルトにフォールバック。
  - 停止フラグ（data/stop_requested.flag）検知によるグレースフルシャットダウン。
  - 監視は環境（development/paper_trading/live）に関わらず本番の sqlite_path を使用する仕様。

- 実行エンジン起動（run_execution）
  - run_execution スクリプトを追加。ExecutionEngine を組み立ててセッション実行するエントリポイント。
  - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組み立て、ExecutionEngine 起動、PID ファイル管理、停止フラグ監視を実装。
  - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を追加。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順の候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重の重み計算。全銘柄スコアが 0 の場合は等重にフォールバック（警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有に基づくエクスポージャ計算、当日売却予定の銘柄を除外可）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す関数。未知レジームはフォールバック（ログ警告）。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算を実装（allocation_method = "risk_based" | "equal" | "score"）。損切り率・許容リスク・単元株丸め（lot_size）・max_position_pct・aggregate cap（available_cash）・cost_buffer による保守的見積り、スケーリングと残差配分ロジックを実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200 乖離率を計算。
    - calc_volatility: atr_20、相対 ATR、20日平均出来高、出来高比率などを計算。true_range の NULL 伝播を考慮した実装。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - DuckDB を利用した SQL ベースの高速集計設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）を計算。horizons バリデーションあり。
    - calc_ic, rank, factor_summary: スピアマン IC 計算、ランク付け（同順位の平均ランク）、ファクター統計サマリを実装。
  - research パッケージのエクスポート調整（zscore_normalize を含む）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）に送りセンチメントを算出し、ai_scores テーブルへ書き込むワークフローを追加。
  - 機能: ニュース収集ウィンドウ計算（JST→UTC 変換）、銘柄ごとの記事集約（最大記事数・文字数トリム）、バッチ送信（_BATCH_SIZE）、リトライ（429/5xx/ネットワーク/タイムアウトで指数バックオフ）、レスポンス JSON バリデーション（厳密な JSON フォーマット要求）、スコアの ±1.0 クリップ、部分更新戦略（対象コードのみ DELETE → INSERT）。
  - API キーは引数または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- ツール（kabusys.tools）
  - paper_verification_report: paper_trading DB を解析して検証レポートを生成する CLI ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - デフォルト閾値: 稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - コマンドライン引数で期間（--from/--to）と DB パス（--db）を指定可能。DB が見つからない場合はエラー表示。

- ユーティリティ（kabusys.utils）
  - process_priority:
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）対応でプロセス優先度を設定。未対応 OS やアクセス権不足時は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留め。引数バリデーションと失敗時のフェイルセーフを実装。

### Changed
- DB 初期化と終了処理
  - monitoring / execution 起動時に init_monitoring_db を呼び冪等に監視テーブルを保証。起動終了時に SQLite / DuckDB の接続を確実にクローズするようにした。

- ログレベルと起動時メッセージの整備
  - run_monitoring / run_execution の起動ログ（KABUSYS_ENV 表示、ポーリング間隔表示、停止フラグ検知ログ等）を追加し運用時の可観測性を向上。

- リサーチ関数の不足データハンドリング
  - 欠損データやサンプル不足時に None を返す等の安全策を強化（例: ma200 データ不足、ATR カウント不足、将来リターンのデータ不足など）。

### Fixed
- .env 読み込み時の例外ハンドリングを追加（ファイル読み込み失敗時に warnings.warn）。
- process_priority の未対応 OS ケースをハンドリングし、例外でプロセスが落ちないようにした。
- calc_score_weights の全スコア 0.0 の際に分母ゼロを回避し等金額配分にフォールバックするよう修正（警告ログ発行）。

### Known issues / Notes
- ai/news_nlp モジュールは堅牢な設計（バッチ、リトライ、JSON バリデーション等）を持っていますが、提供されたコードは途中で切れている箇所があり（_fetch_articles の呼び出し以降が断片的）、実稼働前に未実装部分の実装確認・テストが必要です。
- apply_sector_cap 内で price_map による価格が 0.0 の場合にエクスポージャが過小評価される旨の TODO コメントが残っています。将来的に前日終値や取得原価のフォールバックを検討する必要があります。
- position_sizing は現在単一 lot_size を前提としており、将来的に銘柄別 lot_map に拡張する TODO が残っています。
- calc_forward_returns は horizons の最大値に応じてスキャン範囲をカレンダーバッファ（2倍）で限定する設計ですが、極端な営業日不連続等ケースでの検証が推奨されます。

### Breaking Changes
- 初版のため破壊的変更はありません。

---

開発・運用向けの備考や、追加の実装/テスト要件があればこの CHANGELOG を更新してください。