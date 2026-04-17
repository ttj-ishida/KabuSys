# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録されています。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

最初の公開リリース（推測）。KabuSys のコア機能群を実装。主に自動売買の実行基盤、監視、ポートフォリオ構築、リサーチ、ニュース NLP、ユーティリティ、設定管理、検証ツールを含む。

### Added
- 基本ライブラリとエントリポイント
  - パッケージエントリ: kabusys パッケージ（__version__ = 0.1.0）。
  - 起動スクリプト:
    - run_execution.py — ExecutionEngine 起動スクリプト。ExecutionEngine をスレッドで起動し、data/stop_requested.flag を検知して安全に停止できる。KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用して本番データと分離。
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。監視処理は環境に依らず本番 sqlite_path を使用する設計。
  - PID / 停止フラグ連携: 実行用 PID ファイル（data/execution.pid 等）と停止フラグ（data/stop_requested.flag）によるプロセス管理をサポート。

- 設定・環境変数管理
  - kabusys.config.Settings: 環境変数をラップする設定オブジェクトを提供（KABUSYS_ENV, LOG_LEVEL, SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み。OS 環境変数は保護され上書きされない。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応する堅牢なパーサを実装。

- 実行・監視関連
  - プロセス優先度と CPU affinity 管理:
    - utils.process_priority.set_process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定（"high" / "normal" / "low" をサポート）。権限不足などの失敗はログに警告して安全にスキップ。
    - set_cpu_affinity: 指定したコア数へプロセスを固定するユーティリティを提供（権限不足時は警告してスキップ）。
  - 監視 DB 初期化呼び出し（init_monitoring_db を利用して監視テーブルの存在を保証）。

- Execution（発注）周り
  - BrokerClientFactory によるブローカー抽象化。紙取引（paper_trading）モードでは MockBrokerClient を使って data/paper_trading.db に記録して本番 DB と完全分離する設計。
  - ExecutionEngine の組み立て: OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて実行エンジンを起動。RiskManager に対してデフォルトの RiskConfig を渡す（max_position_pct=0.20 等）。
  - エンジンはスレッドで実行され、停止フラグ検知・タイムアウト付き join 等で安全に終了する。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコアで上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計が 0 の場合は等分配にフォールバックして警告ログを出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（1.0/0.7/0.3）。未知レジームは 1.0 でフォールバックし警告。
  - portfolio.position_sizing
    - calc_position_sizes: 重みと候補リスト、現金・現在ポジション・価格情報から発注株数を算出（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）を考慮して縮退スケールし、端数は残差順に lot 単位で配分するロジックを実装。

- リサーチ（DuckDB ベース）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。データ不足時の None 扱い、ウィンドウ内の行数チェックを行う。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons の検証を実施（正の整数かつ 252 以下）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - factor_summary / rank: 基本統計量算出（count/mean/std/min/max/median）とランク計算（同順位は平均ランク）を実装。
  - 設計方針として外部ライブラリに依存せず、DuckDB を SQL と組み合わせて高速に算出する実装。

- ニュース NLP（OpenAI 統合）
  - ai.news_nlp:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコア（-1.0〜1.0）を生成して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、トークン肥大対策（1 銘柄あたり最大記事数・文字数でトリム）、429/ネットワーク断/5xx 等のエラーに対する指数バックオフリトライを実装。
    - 応答のバリデーションとスコアクリップ（±1.0）。部分失敗に備えて書き込みは対象コードを限定して行い、既存スコアの保護を行う設計。
    - ニュースウィンドウ計算ユーティリティ calc_news_window を提供（JST の前日 15:00 〜 当日 08:30 を UTC に変換して比較）。
    - API キー未提供時に明確な ValueError を送出。

- ユーティリティ & ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートを生成する CLI ツール。PAPER_TRADING_SQLITE_PATH 指定可。稼働率・注文成功率・送信率・P95 レイテンシなどを集計して PASS/FAIL 判定（閾値はソース内に定義）。
    - レポートは期間指定（--from / --to）や DB パス指定（--db）で絞り込み可。欠損テーブルに対しては安全に N/A を表示。
  - DB 関連:
    - DuckDB / SQLite の双方を接続して利用する構成をサポート。monitoring 用テーブル初期化関数（init_monitoring_db）を使用して冪等にテーブルを保証。

### Changed
- （初期リリースのため主に追加のみ。以下は設計上の注記）
  - .env 読み込み時の優先順位: OS 環境 > .env.local > .env。既存 OS 環境変数は保護され上書きされない。

### Fixed
- 環境パースの堅牢化:
  - .env 行パーサで export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善。
- portfolio.calc_score_weights:
  - 全銘柄のスコア合計が 0 の場合に等金額配分にフォールバックし、警告ログを記録するように改善。
- position sizing:
  - lot_size 単位での丸め処理および aggregate cap によるスケーリングアルゴリズムを堅牢化（端数配分は残差順で lot 単位追加）。
- research.calc_forward_returns:
  - horizons の入力検証を追加（正の整数かつ <= 252）。
- ニュース NLP:
  - API キー未設定時の明確なエラー通知を追加。

### Known issues / Notes
- ai/news_nlp.py: 長文の処理や API 応答の形式依存に起因する部分失敗に対しては部分的保護（対象コードを絞って書換）を行う設計だが、OpenAI 側のフォーマット変化には注意が必要。実環境では運用前に十分な検証を推奨。
- prices / raw_financials のデータ不足に対しては多くのファクター算出が None を返すため、上流データの充足が重要。
- process priority / cpu affinity のセットはプラットフォームや権限に依存し、失敗した場合は警告ログでスキップされる。運用環境での権限設定を確認してください。
- run_monitoring は監視 DB に常に本番用 sqlite_path を使用する設計（意図的）。テスト環境で別 DB を使いたい場合は設定を明示的に変更する必要あり。

### Security
- 外部 API キー（OpenAI 等）は環境変数で管理する設計。コード内にハードコードされた秘密情報は含まれていない想定。

---

（この CHANGELOG はソースコードを基に推測して作成しています。実際のリリース履歴や日付はプロジェクト実態に合わせて調整してください。）