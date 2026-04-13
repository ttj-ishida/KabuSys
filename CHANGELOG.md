# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルでは主にリポジトリ内の新規実装・重要な挙動・修正点をコードから推測して記載しています。

## [Unreleased]
- ドキュメントやマイナー調整（将来的な変更予定）

## [0.1.0] - 2026-04-13
初回公開リリース。本リリースでは日本株自動売買システム「KabuSys」の核となる実装群を追加しました。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。

- 実行スクリプト / デーモン
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視機能は KABUSYS_ENV に依存せず本番の sqlite_path を使用して監視データを記録。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority を利用）。
    - SQLite / DuckDB 接続の初期化と確実なクローズ処理を実装。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository・OrderManager・RiskManager・Reconciler を組み立てて ExecutionEngine を実行。
    - 起動時にプロセス優先度を設定。

- 設定管理
  - config.py：.env 自動ロード・環境変数ラッパー実装。
    - プロジェクトルート自動探索（.git または pyproject.toml を基準）により CWD 非依存で .env をロード。
    - .env / .env.local の読み込み順序と保護された OS 環境変数の取り扱い（override/protected）を実装。
    - 行パースロジックを強化（export 句、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスでアプリケーション設定をプロパティ経由で提供（env 検証、DB パス、PID/KILL ファイルパス、閾値、PAPER_FILL_MODE 検証等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。

- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を呼ぶ箇所を追加（run_monitoring/run_execution）して監視テーブルの冪等な作成を保証。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py：Paper Trading 検証レポート生成 CLI を追加。
    - DB パスは引数 (--db)・環境変数(PAPER_TRADING_SQLITE_PATH)・デフォルトの順で解決。
    - 指定期間（--from / --to）でシステム安定性（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計してレポート出力。
    - 閾値（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）を定義して PASS/FAIL 判定を実施。
    - DB 未存在やテーブル欠損時に安全に N/A を返す設計。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py：候補選定（select_candidates）、等配分（calc_equal_weights）、スコア配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py：セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。
    - セクター露出計算、売却予定銘柄の除外、"unknown" セクター扱いの挙動を明記。
    - レジームに応じた乗数（bull=1.0, neutral=0.7, bear=0.3）を提供し未知レジームはフォールバック。
  - portfolio/position_sizing.py：株数計算ロジック（risk_based / equal / score）を実装。
    - 各種制約（単元 lot_size、1 銘柄上限、aggregate cap、cost_buffer）を考慮した株数決定・スケールダウンロジックを提供。
    - aggregate cap を超える場合のスケーリングと lot 単位での再分配アルゴリズムを実装。
  - portfolio/__init__.py：主要関数を公開。

- 研究・ファクター計算
  - research/factor_research.py：Momentum / Volatility / Value ファクター計算を DuckDB SQL ベースで実装。
    - mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等を計算。
    - 各関数は prices_daily/raw_financials を参照し、データ不足時は None を返す設計。
  - research/feature_exploration.py：将来リターン計算、Spearman IC 計算、ファクター統計サマリ、ランク関数を実装。
    - calc_forward_returns は複数ホライズン対応、ホライズン引数検証を実装。
    - calc_ic は 3 件未満で None を返す安全設計。
    - factor_summary で count/mean/std/min/max/median を返す。
  - research/__init__.py：主要 API を公開（zscore_normalize は data.stats 由来）。

- AI ニュース NLP
  - ai/news_nlp.py：raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores に書き込む処理を実装。
    - ニュース集約ウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ（calc_news_window）。
    - 記事は銘柄ごとに最大記事数・文字数でトリムし、最大 20 銘柄単位でバッチ送信。
    - API 呼び出しは 429 / ネットワーク / 5xx に対する指数バックオフでリトライ（上限あり）。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時のテーブル更新戦略を採用（DELETE→INSERT を銘柄絞りで実行）。
    - OpenAI API キー未設定時は明確な ValueError を送出。
    - フェイルセーフ: API 失敗はスキップして処理継続。

- ユーティリティ
  - utils/process_priority.py：プロセス優先度設定・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定可能（None で無効）。
    - 権限不足や未対応 OS に対しては警告を出してスキップする安全処理。

### Changed
- なし（初回リリース）

### Fixed
- 環境変数/設定の堅牢化
  - .env パースの強化により export 句、クォート内のエスケープ、インラインコメントの正しい処理を実現（config._parse_env_line）。
  - MONITOR_POLL_INTERVAL の不正な値に対するフォールバックと警告ロギングを追加（run_monitoring._get_poll_interval）。
  - process_priority の権限不足や未実装 API に対して警告を出して安全にスキップするように（utils.process_priority）。

### Security
- なし

### Notes / Implementation details
- DB 接続
  - 監視処理（run_monitoring）は監視用テーブルを作成するために常に Settings.sqlite_path（本番 DB 想定）を使用します。これにより監視は環境設定に依存しない一貫した記録が可能です。
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB とデータ分離を行います。
- DuckDB は大規模データ処理（prices_daily/raw_financials/ai_scores 等）に使用されています。複雑な SQL ウィンドウ関数を活用した実装により多くの集計を DB 側で効率的に実行します。
- CLI ツール（paper_verification_report）は DB スキーマ欠如時に安全に N/A を返し、運用での突発的なテーブル欠損に耐える設計です。

もし CHANGELOG に追加してほしい箇所（例えば特定モジュールの詳細、リリース日変更、既知の制限や TODO）があれば指示ください。