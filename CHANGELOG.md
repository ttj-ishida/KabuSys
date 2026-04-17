# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。セマンティックバージョニングを使用します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。自動売買システム「KabuSys」の基本コンポーネントを実装しました。以下はコードベースから推測される主要な追加・改善点と注意点です。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - BrokerClientFactory を用いて本番／ペーパートレードでブローカークライアントを切り替え。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する設計。
    - エンジンはバックグラウンドスレッドで実行され、プロセス内の停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - 実行中 PID を data/execution.pid に記録する想定（pid_file の取り扱いあり）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計（監視データは一元管理）。
    - 停止フラグと例外ハンドリングを備えたポーリングループを実装。

- 設定と環境変数ロード
  - config.Settings クラスを導入し、環境変数経由で各種設定を提供。
  - 自動 .env 読み込み:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env`（優先度低）および`.env.local`（優先度高）を自動読み込み（OS 環境変数は保護）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの適切な取り扱い等を実装。
  - 各種設定プロパティを実装:
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/kill フラグ、閾値（CPU/MEM/DISK）、ログレベル、環境種別（development/paper_trading/live）等。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
    - is_live / is_paper / is_dev のブールプロパティ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選出（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分 / スコア加重（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を越えるセクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear を実装、未知値は 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）をサポート。
    - 単元株（lot_size）単位で丸め、per-stock 上限・aggregate cap（利用可能現金）に応じてスケールダウンするロジックを実装。
    - cost_buffer を用いた保守的コスト見積り、端数配分（残余キャッシュに応じて lot 単位で再配分）を実装。

- 研究／リサーチ機能（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率を計算（データ不足は None を返す）。
    - calc_volatility: ATR(20)、相対ATR、20日平均出来高、出来高比率を計算。
    - calc_value: PER・ROE を raw_financials と prices_daily から算出（target_date 以前の最新財務データを使用）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン (1,5,21 日等) を計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効データが 3 件未満の場合は None）。
    - factor_summary / rank: 基本統計量と順位付けユーティリティを実装。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から再エクスポート。

- AI ニュース NLP スコアリング
  - ai.news_nlp モジュール（OpenAI を利用）を追加:
    - raw_news と news_symbols を集約して銘柄ごとにテキストを生成し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む。
    - バッチサイズ、1 銘柄あたりの最大記事数 / 文字数制限、JSON モード厳格出力を採用。
    - 429 / ネットワーク断 / 5xx に対する指数バックオフによるリトライ、レスポンスのバリデーション、スコアの ±1.0 クリッピング、部分失敗時の保護（影響コードだけ置換）などのフェイルセーフ実装。
    - calc_news_window ユーティリティ（JST の前日 15:00 〜 当日 08:30 を UTC で扱う変換）を提供。

- 書類/ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）等。
    - P95 計算、期間フィルタリング、閾値（稼働率 99% など）による PASS/FAIL 判定、DB が存在しない場合のエラーメッセージを実装。
    - コマンドライン引数 --from/--to/--db に対応。

- DB/データ接続
  - DuckDB を用いた分析用接続サポート（duckdb_conn を多数のコンポーネントで受け渡し）。
  - 監視用テーブルの初期化関数 init_monitoring_db を呼ぶ箇所を run_monitoring/run_execution に追加し、監視テーブルが存在することを保証（冪等）。

- ユーティリティ
  - utils.process_priority:
    - プロセス優先度（Windows の優先度クラス／POSIX の nice 値）を抽象化して設定する set_process_priority を実装。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能（例外時はワーニングでスキップ）。
  - 停止フラグ / PID ファイルを用いた起動停止の制御を多数のコンポーネントで採用。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- 環境変数・設定周りの堅牢化:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や文字列等）をログで警告しデフォルトにフォールバックするように実装（run_monitoring）。
  - .env 読み込み失敗時に警告を出す安全なハンドリング（読み込み失敗で例外吐かない）。
- 実行ループの堅牢化:
  - run_monitoring のポーリング中に monitor.check_once() が例外を投げてもループを継続し、例外のトレースをログ出力するように変更。
  - run_execution は停止フラグを検知すると Engine.stop() を呼んで安全にシャットダウンするロジックを実装。
- tools.paper_verification_report:
  - DB が存在しない場合のユーザーフレンドリーなエラーメッセージ。
  - SQL 実行でテーブルが存在しない場合に OperationalError を捕捉して安全にレポートを作成（N/A 表示）。

### 注意点 / 既知の制約 (Known issues)
- DuckDB / SQLite のスキーマや外部テーブルの存在が前提。実データが無い環境ではいくつかの出力が N/A になります。
- position_sizing の価格欠損時（price が 0.0 や None）の扱い:
  - 現在は 0.0 を使用するとエクスポージャーの過小見積りやスキップにつながるため、将来的に前日終値や取得原価をフォールバックする改善が必要とされています（TODO コメントあり）。
- ai.news_nlp モジュールは OpenAI API キーが必須。キー未設定時は ValueError を送出する。
- process_priority / cpu_affinity の設定はプラットフォームや権限に依存し、失敗時はワーニングにとどめる設計。
- Paper Trading（ペーパー用 DB）と本番 DB は分離設計だが、操作ミスで同じパスを指定した場合の保護は呼び出し側の注意が必要。

### セキュリティ (Security)
- なし

---

この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やコミットメッセージと異なる場合があります。リリースの際はコミット履歴やリリースノートを元に適宜調整してください。