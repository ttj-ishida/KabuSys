# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 実行用スクリプトを追加
  - run_execution.py:
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、EngineConfig を指定して ExecutionEngine をスレッドで起動。
    - 停止フラグ (data/stop_requested.flag) と実行用 PID ファイル (data/execution.pid) をサポート。停止フラグ検知時に安全に停止処理を実行。
    - 起動時にプロセス優先度を "high" に設定。

- 監視用スクリプトを追加
  - run_monitoring.py:
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視処理は環境にかかわらず本番用の sqlite_path（data/monitoring.db を想定）を使用する設計。
    - 停止フラグ (data/stop_requested.flag) およびプロセス優先度設定をサポート。例外はログに残して次回ポーリングへフォールバック。

- 設定 / 環境変数管理を強化
  - config.py:
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは `export KEY=val` 形式やクォート文字列、インラインコメント（クォート無しでの # 扱い）に対応。
    - 設定取得用の Settings クラスを提供（多くのプロパティで必要値チェックや値の検証を実施）。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の検証を導入（不正値時は ValueError）。

- ポートフォリオ構築機能
  - portfolio.portfolio_builder:
    - BUY シグナルから候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時は等配分へフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有比率が max_sector_pct を超える場合に同一セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供（未知レジームはワーニングを出して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数決定、単元株丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリングと端数処理を実装。
    - cost_buffer を受け取り手数料・スリッページを保守的に見積もる処理を組み込み。

- 研究 (research) 機能
  - research.factor_research:
    - モメンタム / ボラティリティ / バリュー系ファクター計算を DuckDB 上の prices_daily / raw_financials テーブルから実装（calc_momentum / calc_volatility / calc_value）。
    - MA200・ATR 等のウィンドウベース集計を考慮し、データ不足時は None を返す設計。
  - research.feature_exploration:
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク付け (rank) を追加。
    - 標準ライブラリのみで実装、horizons のバリデーション等を実施。

- AI ニュース NLP モジュール
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルへ書き込むフローを実装。
    - バッチ（最大 20 銘柄/呼び出し）、記事数/文字数のトリム、429/ネットワーク/5xx に対する指数バックオフによるリトライ、レスポンスの厳格なバリデーション、スコアの ±1.0 クリップ、部分的な DB 更新（対象コードのみ置換）などのフェイルセーフ設計を導入。
    - ニュース収集ウィンドウ計算ユーティリティ calc_news_window を提供（JST ベースの時間窓を UTC naive datetime に変換）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート出力スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ (平均/最大/P95) を集計して判定（PASS/FAIL）を出力。
    - デフォルト DB は data/paper_trading.db。コマンドライン引数で期間や DB パスを指定可能。
    - P95 計算、日付フィルタ、欠損テーブル時の安全ハンドリングを実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、権限不足や未対応環境では警告を出して安全にスキップ。

### Changed
- DB/接続周りの安全性・リソース管理を強化
  - run_monitoring.py / run_execution.py で DB 接続を finally ブロックで確実に close。
  - monitoring 起動時に監視テーブル初期化 (init_monitoring_db) を行い、初回起動や空 DB への耐性を確保。

- 設定の取り扱い改善
  - .env の読み込み順序と上書きポリシー（.env.local が .env を上書き）が明確化され、OS 環境変数は保護されるようになった。

### Fixed
- 環境変数パースに関する堅牢化
  - _parse_env_line がクォート文字列内のエスケープや inline コメントの扱いを改善し、誤ったキー/値の読み込みを防止。
- モジュールのフェイルセーフ挙動
  - monitoring のポーリングループ内で check_once() が例外を投げてもループを継続するように例外をキャッチしてログ出力。KeyboardInterrupt による終了処理を適切にログ出力して DB をクローズ。

---

## [0.1.0] - 初期リリース
- パッケージ基本情報
  - kabusys.__version__ = 0.1.0
  - パッケージ構成: data, strategy, execution, monitoring 等の主要モジュールをエクスポート。

- 提供機能の概要
  - 実運用向けの Execution エンジンと Monitoring を起動するスクリプト群。
  - .env ベースの設定読み込み・検証を行う Settings。
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）、セクターキャップ、レジーム乗数。
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）および研究用途のユーティリティ（将来リターン、IC、統計サマリー）。
  - OpenAI を用いたニュース NLP スコアリングの基盤（バッチ・リトライ・検証・DB 書き込み戦略）。
  - Paper Trading 用の検証レポート生成ツール。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。

注記:
- ここで記載した変更点・振る舞いはソースコードから推測したものであり、実際の運用設定や追加の未公開コードにより細部が異なる場合があります。必要であれば特定ファイルや機能についてさらに詳しい説明を作成します。