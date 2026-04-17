# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを想定します。

## [Unreleased]

（現在のソースから判断すると、主要な機能は 0.1.0 としてリリース済みの想定です。本節は空にしてあります。）

---

## [0.1.0] - 初回リリース

リリース日: 未設定

概要: 日本株自動売買システム "KabuSys" の初回リリース相当。監視・実行エンジン、ポートフォリオ構築・サイズ決定ロジック、リサーチ（ファクター計算・特徴量解析）、ニュースNLPスコアリング（OpenAI 連携）、ユーティリティとコマンドラインツールを含む。

### 追加 (Added)
- 全体
  - パッケージ初期版を追加。モジュール群を整理して公開。
  - バージョン情報: kabusys.__version__ = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用する設計。
    - 停止用フラグファイル (data/stop_requested.flag) を検知して優雅に停止。
    - check_once() 実行時に例外が発生してもループは継続する（ログ出力）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（settings.paper_sqlite_path）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てを行う。
    - エンジンは別スレッドで run_session を実行し、同様に停止フラグ (data/stop_requested.flag) を監視して停止する。
    - 実行用 pid ファイル (data/execution.pid) のパスを管理。

- 設定管理
  - config.py
    - .env 自動ロード機能を提供（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装: export 付き行、引用符内のバックスラッシュエスケープ、コメント処理などに対応。
    - Settings クラスを提供し、各種設定値（API トークン、データベースパス、Paper Trading 関連設定、閾値、環境判定等）をプロパティ経由で取得可能。
    - PAPER_FILL_MODE（paper trading の MockBroker の fill モード）を検証（有効値: instant/partial/never/reject）。
    - 環境（KABUSYS_ENV）とログレベル検証ロジックを内蔵。

- 監視・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動処理（実行/監視）で呼び出し、監視用テーブルの存在を保証（冪等）。

- プロセス管理ユーティリティ
  - utils/process_priority.py
    - プロセス優先度の設定機能を追加（set_process_priority）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を抽象化して対応。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定するユーティリティを追加。
    - アクセス権限不足や未サポート環境では警告を出してスキップするフェイルセーフ実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を追加。全スコアが 0 の場合は等金額にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用するロジックを追加。既存ポジションのセクター別エクスポージャー計算、上限を超えるセクターの新規候補除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear ⇒ 1.0/0.7/0.3）を実装。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）で丸め、ポジション上限（max_position_pct）・投下上限（max_utilization）・コストバッファ（cost_buffer）を考慮したスケーリング、残差処理（fractional remainders による追加配分）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を計算（DuckDB SQL）。
    - calc_volatility: ATR(20)・相対ATR・20日平均売買代金・出来高比を計算。
    - calc_value: raw_financials を用いた PER・ROE 計算（直近レポートを取得）。
    - 全関数は DuckDB 接続を受け取り、prices_daily/raw_financials を参照して純粋関数的に結果を返す。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons の妥当性検証あり。
    - calc_ic: スピアマン（ランク相関）による IC 計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリを実装。
    - 標準ライブラリのみで実装（pandas など外部依存なし）。

- ニュースNLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news を集約して OpenAI (gpt-4o-mini) に送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装（バッチ処理、最大 20 銘柄/呼び出し）。
    - スコアのクリップ（±1.0）、API レスポンスのバリデーション、429/ネットワーク/5xx に対する指数バックオフのリトライを実装。
    - ニュース収集ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB 比較）。
    - 入力トークン肥大化対策: 1 銘柄あたり最大記事数・文字数を制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API キー未設定時は ValueError を送出するチェック。
    - ※一部実装はファイル末尾で切れている（ソース断片）。完遂部分は上記フローに沿う設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（コマンドライン実行可能）。
    - 検証指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 日付フィルタ対応（--from / --to）、P95 計算、簡易 Pass/Fail 判定の出力を実装。

### 変更 (Changed)
- 実行時のプロセス優先度設定を startup で "high" に設定する運用方針を導入（run_monitoring/run_execution の最初の処理）。
- 監視データベース初期化を起動時に必ず（冪等に）実行することで監視テーブルの存在を保証。

### 修正 (Fixed)
- 設計上のフェイルセーフを多数導入:
  - process_priority/set_cpu_affinity: 権限不足や未対応 OS 時に例外で止めず警告でスキップする。
  - run_monitoring: check_once() が例外を投げてもポーリングループを継続する（ログ出力）。
  - .env 読み込み: ファイル読み込み失敗時に警告で継続。

### 注意点 / 既知の制約 (Known Issues)
- ai/news_nlp.py はソース末尾が切れており、完全実装が確認できない箇所が存在する。リトライ・DB 書き込みの最終処理部分はソース全体の確認が必要。
- position_sizing の価格欠損時（price が 0.0）の扱いについて TODO コメントあり。将来的に前日終値や取得原価によるフォールバックを検討予定。
- .env パーサは多くのケースに対応しているが、非常に特殊な .env フォーマットの全パターンの検証は未実施。
- DuckDB を用いるリサーチ系関数は価格・財務データテーブル（prices_daily / raw_financials）が期待フォーマットで存在することを前提としている。

### セキュリティ (Security)
- 特になし。

---

注: 上記は提供されたソースコードから推測して作成した CHANGELOG です。リリース日・細かい修正履歴等は実際のコミットログを参照して補完することを推奨します。必要であれば、各モジュールの詳細（例: 引数の説明、返り値サンプル、例外一覧など）を含めたリリースノートの拡張版を作成します。