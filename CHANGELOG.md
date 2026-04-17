# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17 (初回リリース)
初期リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - モジュール単位でのエクスポートを整備（kabusys.portfolio, kabusys.research 等）。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出を行い、OS 環境変数を保護して読み込み）。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメント処理など）。
  - 環境変数取得用 Settings クラスを実装。多くの設定プロパティを提供:
    - J-Quants / kabuAPI / LINE 関連トークン
    - duckdb / sqlite / paper_trading 用 DB パス
    - PAPER_FILL_MODE（paper_trading の fill モード検証）
    - PID / kill フラグ関連パスおよび挙動設定
    - CPU/メモリ/ディスク閾値
    - KABUSYS_ENV / LOG_LEVEL の検証ロジック
  - settings インスタンスをモジュールレベルで公開。

- 実行・監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（paper_trading 用の Mock を利用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - execution.pid の管理、data/stop_requested.flag による外部停止処理をサポート。
    - プロセス優先度を最初に "high" に設定する処理を実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）。
    - 停止フラグ検知でループ終了、例外時はログ出力して次回まで待機。

- 監視 DB 初期化
  - monitoring_db 用初期化ユーティリティ（init_monitoring_db）を起動スクリプトから利用（監視テーブルの存在保証）。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装（Windows / POSIX の差分吸収、権限エラーは警告で無視）。
  - set_cpu_affinity(cpu_count) を実装（指定コア数でプロセスをピン留め、権限エラーは警告で無視）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: スコア降順 + signal_rank タイブレークによる候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が上限超過の場合に新規候補を除外、"unknown" セクターは適用外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは警告の上 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: 重み・候補・リスクベースの各手法に対応した株数算出ロジックを実装（単元丸め、max_position_pct / max_utilization / cost_buffer 等考慮）。
    - aggregate cap によるスケールダウンと端数処理（lot_size 単位での再配分）を実装。
    - risk_based モード: リスク許容率・利食い/損切り想定に基づく算出を実装。

- 研究・リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB の prices_daily / raw_financials を参照、ウィンドウ判定・欠損取扱いあり）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算（入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・欠損除外・最小レコード数チェック）。
    - factor_summary / rank: 基本統計量・ランク計算ユーティリティを実装。
  - research パッケージの公開 API に zscore_normalize を含める（kabusys.data.stats からインポートしてエクスポート）。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news の記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ保存する処理を実装。
  - スコアリング設計:
    - ニュースウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC 比較用に変換）。
    - 銘柄ごとに記事集約（最大記事数・最大文字数でトリム）。
    - 1 API コールあたり最大 20 銘柄でバッチ送信、429/5xx/タイムアウトは指数バックオフでリトライ。
    - レスポンスバリデーション、スコアを ±1.0 にクリップ、部分更新（該当コードのみ置換）で部分失敗時の保護。
    - API キー未提供時は明示的にエラーを返す。

- ツール (kabusys.tools.paper_verification_report)
  - paper_trading 用検証レポート生成スクリプトを追加。
    - 任意期間フィルタ（--from / --to）対応、PAPER_TRADING_SQLITE_PATH で DB 指定可。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - P95 計算、各種閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）を定義。

### 変更 (Changed)
- 設定読み込みの優先順位を明確化（OS 環境 > .env.local > .env）。.env.local は OS の既存環境変数を保護しつつ上書き可能。
- Execution / Monitoring 起動時にプロセス優先度を自動で "high" に設定するように変更（起動直後に実行）。

### 修正 (Fixed)
- .env ファイル読み込み失敗時に警告を出力して無視する実装を追加（テスト・権限問題に対する耐性向上）。
- calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックし警告を出すよう修正。

### 注意点 / TODO
- risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過小見積りされてしまう旨の TODO コメントあり。将来的に前日終値や取得原価のフォールバックを検討予定。
- position_sizing.calc_position_sizes: lot_size を銘柄別に持たせる拡張（stocks マスタからの取得）は将来対応予定。
- ai.news_nlp モジュールは外部 API（OpenAI）に依存するため、APIキー管理・エラーに対する運用ルールが必要。
- run_monitoring.run と run_execution.run は停止フラグ（data/stop_requested.flag）や PID 管理に依存しているため、運用環境で data ディレクトリや権限の整備が必要。

### セキュリティ (Security)
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや機密環境向け）。
- .env の読み込みでは OS 環境変数を保護する設計（.env による既存 OS 環境の上書きを抑止）。

---

今後のリリースでは、テスト追加（特に経済指標・NLP 部分の回帰テスト）、duckdb に対するバルク書き込みの堅牢化、銘柄単位 lot_size/手数料モデルの拡張を予定しています。必要であればこれらを CHANGELOG の Unreleased セクションとして分割して記載できます。