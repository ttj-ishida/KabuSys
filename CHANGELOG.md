# CHANGELOG

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティクスは慣習に従っています。

最新変更は上部に記載しています。

## [Unreleased]

- 注意: 現在の開発中コードには ai/news_nlp.py の末尾が途中で切れている断片があります（実装未完）。実運用前にこの部分の補完が必要です。

---

## [0.1.0] - 2026-04-17

初回リリース — 基本的な自動売買・調査・監視ユーティリティ群を追加。

### 追加 (Added)
- パッケージの基本情報
  - kabusys パッケージ初期バージョンを追加。バージョン: 0.1.0（src/kabusys/__init__.py）

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視起動時にプロセス優先度を "high" に設定。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨をドキュメント化。
    - 停止フラグファイル（data/stop_requested.flag）で安全にループ停止。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を介してブローカークライアントを組み立て、OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を起動。
    - エンジン起動前に停止フラグを検査し、安全に開始/停止を行う。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 & 環境読み込み
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順序、OS 環境変数保護（protected keys）に対応。
    - export KEY=val、引用符付き値、コメント取り扱い等を考慮した .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを実装し、各種設定値（DBパス、APIトークン、監視閾値、KABUSYS_ENV 検証等）をプロパティで提供。
    - 設定値の検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を実装。

- モジュール群: ポートフォリオ構築・リスク管理・ポジションサイズ決定
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・同点タイブレーク実装。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別エクスポージャー計算に基づく候補除外機能（売却予定コードの除外対応）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（未知のレジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積）を反映。
    - 利用可能現金に応じたスケーリング時に残差配分ロジックを実装（lot_size 単位で追加配分）。

- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db への参照（run_* スクリプトから init_monitoring_db を呼び出し、監視用テーブルの冪等初期化を保証）。

- 実行ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。権限不足や未対応 OS は警告でスキップ。
    - set_cpu_affinity(cpu_count): CPU affinity を最初の N コアに固定するユーティリティ（エラー時は警告でスキップ）。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算（NULL/データ不足対応）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得）。
  - research.feature_exploration
    - calc_forward_returns: 指定 horizon の将来リターンを計算（複数ホライズン同時処理、入力検証）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損処理・最小サンプルチェック）。
    - factor_summary, rank: ファクター統計サマリーとランク変換ユーティリティ。

- AI: ニュース NLP（ニュースセンチメント）
  - ai.news_nlp
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を取得する設計を追加。
    - バッチ処理（最大 20 銘柄）、トークン肥大対策（記事数・文字数制限）、JSON Mode 出力を期待する設計。
    - 429 / ネットワーク / 5xx に対する指数バックオフリトライ（上限あり）、レスポンス検証、スコアクリップ、部分成功時の DB 更新方針（対象コードのみ置換）を実装方針として記載。
    - calc_news_window: target_date に対するニュース集計ウィンドウ計算を実装（JST→UTC 変換、境界は前日 15:00 JST〜当日 08:30 JST）。
    - 実装は堅牢性を意識しているが、ファイル末尾が未完のため現状は部分実装。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出し閾値判定で PASS/FAIL を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、CLI オプション (--from/--to/--db) を提供。
    - デフォルトしきい値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）。

### 変更 (Changed)
- 設定読み込みのデフォルト挙動
  - .env の自動ロードを導入。プロジェクトルートが特定できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 設定でスキップされる点をドキュメント化。

### 修正 (Fixed)
- N/A（初回リリース）

### 既知の問題 (Known issues)
- ai/news_nlp.py の末尾が途中で切れており、関数 score_news の続きが欠落しています。OpenAI との通信周り・DB 書き込みロジックは設計上存在しますが、現状は動作確認できません。実運用前にファイルの補完と単体テストが必須です。
- apply_sector_cap の価格欠損（price が 0.0 の場合）でエクスポージャーが過少見積もられる可能性があり、コメントに将来的なフォールバック価格対応（前日終値や取得原価）を検討する旨が残されています。
- position_sizing の将来的拡張点として銘柄別 lot_size（単元）対応が TODO に記載されています。

### マイグレーションメモ / 運用上の注意
- 監視(run_monitoring)は説明にある通り「環境にかかわらず本番 sqlite_path を使用」します。環境毎に監視 DB を分けたい場合は実装を修正して運用してください。
- Paper Trading 実行時は run_execution が PAPER_TRADING_SQLITE_PATH（またはデフォルト data/paper_trading.db）を使用して本番 DB と分離します。紙上テスト時は環境変数 KABUSYS_ENV=paper_trading を設定してください。
- .env の自動ロード挙動により OS 環境変数が保護されます。CI/テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を利用する機能は API キー (OPENAI_API_KEY) が必要です（ai.news_nlp.score_news は api_key 引数または環境変数を参照）。上記の既知の問題（実装未完）に注意してください。

---

これ以降のリリースでは以下を予定しています（TODO）
- ai/news_nlp の完全実装と単体テスト、API エラー/失敗ケースに対する堅牢な再試行と部分的ロールバック戦略の検証
- apply_sector_cap の価格フォールバック実装
- 銘柄別 lot_size 対応（position_sizing）
- 監視・実行周りの E2E テストケース整備とドキュメント強化

---

ライセンスやセキュリティの記載が必要な場合は別途追記してください。