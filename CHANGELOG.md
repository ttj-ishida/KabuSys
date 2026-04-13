CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠  
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- docs: 開発中/未リリースの変更点はありません（初回リリースを参照してください）。

[0.1.0] - 2026-04-13
-------------------
初回公開リリース。本プロジェクトは日本株自動売買システム「KabuSys」の基礎コンポーネント群を実装しています。以下はコードベースから推測した主要な追加・設計方針・挙動です。

Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - ロギングを各モジュールで利用する仕組みを導入。

- 設定管理 (src/kabusys/config.py)
  - 環境変数 / .env 自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込み。
    - .env.local は .env を上書きする（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサを実装し、export プレフィックス・クォート文字列・エスケープ・インラインコメントに対応。
  - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / CPU/MEMORY/DISK 閾値 / KABUSYS_ENV / LOG_LEVEL など）。
  - KABUSYS_ENV の妥当性検査（development / paper_trading / live）と LOG_LEVEL の検証を実装。

- 起動スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するエントリポイント。
    - Paper trading 環境 (KABUSYS_ENV=paper_trading) の場合は専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを選択・初期化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築しセッション実行。
    - プロセス優先度を起動時に "high" に設定。

  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor をポーリングで実行するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視用 DB を確実に接続）。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルの存在を冪等に保証（両起動スクリプト内で使用）。

- utils/process_priority (src/kabusys/utils/process_priority.py)
  - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装。
    - Windows は psutil の HIGH_PRIORITY_CLASS 等を使用。
    - POSIX 系（Linux, Darwin, FreeBSD）は nice 値を設定。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留め可能（権限不足や未対応 API の場合は警告でスキップ）。

- ポートフォリオ構築 (src/kabusys/portfolio)
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0.0 の場合に等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）を追加。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をサポートし、未知のレジームは 1.0 でフォールバック（警告ログ出力）。
    - apply_sector_cap は既存ポジションのセクター別時価を計算しセクター上限超過時に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
  - position_sizing: calc_position_sizes を追加。allocation_method に応じた株数計算（risk_based / equal / score）を実装。
    - lot_size（単元）で丸め、per-position 上限や aggregate cap（available_cash 超過時のスケーリング）を考慮。
    - cost_buffer による手数料・スリッページの保守的見積りをサポート。
    - 価格欠損時はスキップしてログ出力。

- 研究・リサーチ (src/kabusys/research)
  - factor_research: モメンタム（calc_momentum）、ボラティリティ・流動性（calc_volatility）、バリュー（calc_value）を実装。DuckDB の prices_daily / raw_financials を参照して計算。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）を実装。
    - calc_forward_returns は複数ホライズンに対応し、horizons のバリデーションを実施。
    - calc_ic は Spearman ランク相関（ties を平均ランクで扱う）を実装。

- AI / ニュース (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込むロジックを追加。
    - ニュース集計ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算するユーティリティを提供（calc_news_window）。
    - 1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄/チャンクでバッチ化して API 呼び出し、429/ネットワーク/5xx は指数バックオフでリトライ。
    - レスポンス検証、スコアを ±1.0 にクリップ、取得した銘柄のみ差し替え（DELETE → INSERT）して部分失敗時の保護を実施。
    - API キーが未設定の場合は ValueError を送出。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成スクリプトを追加。
    - CLI で期間（--from / --to）と DB パス（--db）を指定可能。
    - system_status / trade_logs / risk_logs の集計に基づき稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出し、閾値に対する PASS/FAIL 判定を出力。
    - P95 は独自実装。DB テーブル欠損時は適切に N/A を表示。

Changed
- DB 統合
  - DuckDB を分析用 DB（prices_daily, raw_financials など）として導入。DuckDB 接続を受け取る設計により SQL と Python の組合せで高速集計が可能。
  - 監視/実行スクリプトで duckdb_conn を生成して渡すようになっている。

- 起動時のプロセス優先度
  - run_execution/run_monitoring 共に最初に set_process_priority("high") を呼び出し、重要プロセスの優先度を上げる方針を採用。

Fixed
- 設定ロードの堅牢化
  - .env 行パーサでエスケープやクォート、export キーワード、インラインコメントを正しく扱うことで .env の柔軟な記述を許容。
  - .env ファイル読み込みで OS 環境変数を protected として上書きを防ぐ仕組みを実装。

- 計算上の安全性
  - calc_score_weights: 全スコア合計が 0 の場合にゼロ除算を避け等金額配分にフォールバック。
  - research モジュールや position_sizing モジュールでデータ欠損時に None やスキップを返すことで例外発生を抑止。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は明示的にエラーを出すことで誤動作を回避。

Notes / Implementation details
- 多くの関数は「DB 参照なし」の純粋関数として設計されており、ユニットテストが容易（ポートフォリオ関連関数など）。
- DuckDB の executemany やパラメータ仕様に注意した実装（コメントで言及あり）。
- 実際のブローカーや ExecutionEngine 実装の詳細は本ログからは推測できないため、BrokerClientFactory・ExecutionEngine 等は抽象化された依存として存在する。

今後の改善余地（コードから推測）
- position_sizing の price 欠損時フォールバック（前日終値など）を実装すると安全性が向上。
- apply_sector_cap の "unknown" 扱いに関するポリシー明確化（現在は制限を適用しない）。
- CPU affinity の Windows 対応と権限不足時のリカバリ戦略。
- AI スコアリングの部分失敗時のリトライ/ロールバック戦略の拡充とメトリクス計測。

以上。必要であれば各変更点をより詳細に分割したバージョン履歴（マイナー/パッチ単位）や、リリースノート用の英語版も作成します。どの粒度で記載するか指定してください。