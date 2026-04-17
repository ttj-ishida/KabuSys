# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。  

※この履歴はコードベースの内容から推測して作成しています。

## [Unreleased]

### Added
- 環境設定周り（kabusys.config）
  - プロジェクトルート自動検出機能を追加（.git / pyproject.toml を探索）。これによりパッケージ配布後も .env 自動ロードが機能する。
  - .env ファイルパーサの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース処理
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみコメントとみなす）
  - OS 環境変数を保護するための上書き制御（protected set）を導入。`.env.local` を上書きモードで読み込みつつも既存の OS 環境変数は保護する。
  - 自動 .env ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `paper_trading` 環境では MockBrokerClient を利用し、paper_trading 用 DB（既定: data/paper_trading.db）を使用して本番 DB と分離。
    - Broker クライアントファクトリ（BrokerClientFactory）からブローカーを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行・監視。停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - デフォルトのリスク設定を RiskConfig として組み込み（max_position_pct, max_utilization, rate_limit など）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（既定 60 秒）。不正値は警告を出して既定にフォールバック。
    - 監視用 DB は実行環境にかかわらず本番 sqlite_path を使用して監視データを一元化。
    - プロセス優先度を最初に "high" に設定する処理を導入。
    - 停止フラグファイル検出でループを抜け、接続を確実にクローズして終了。

- モジュール追加 / 充実
  - portfolio:
    - 銘柄候補選定・スコアベース/等金額配分（select_candidates、calc_equal_weights、calc_score_weights）。
    - セクター集中制限とレジーム乗数（apply_sector_cap、calc_regime_multiplier）。
    - 株数決定ロジック（calc_position_sizes）を実装（risk_based / equal / score の各方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer 対応）。
  - research:
    - ファクター計算（calc_momentum、calc_volatility、calc_value）を DuckDB 経由で実装。価格・財務データを用いた複数ファクターを算出。
    - 研究向けユーティリティ（calc_forward_returns、calc_ic、factor_summary、rank）を追加。IC（Spearmanランク相関）や統計サマリに対応。
    - DuckDB クエリで窓関数や LAG/LEAD を使いパフォーマンスを考慮した実装。
  - ai:
    - news_nlp モジュールを追加（OpenAI API を用いたニュースのセンチメントスコアリング設計）。
      - バッチ処理（銘柄ごとに最大記事数・文字数でトリム、最大 20 銘柄まで / API 呼出し）・リトライ（429/ネットワーク/5xx に対する指数バックオフ）などを計画。
      - スコアは ±1.0 にクリップし、DB（ai_scores）への部分置換方式で書き込み（部分失敗時の保護）。
      - ニュース収集ウィンドウ計算（JST → UTC 変換）ユーティリティを実装。
    - （注）news_nlp は途中実装の箇所が見られ、未完成部分が存在する可能性あり。

  - tools:
    - paper_verification_report：Paper Trading の検証レポート生成 CLI を追加。
      - 稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を算出し PASS/FAIL 判定を行う。
      - CLI オプションで期間指定（--from / --to）や DB パス指定（--db）に対応。
      - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）を設定。

  - utils:
    - process_priority: プロセス優先度設定ユーティリティを追加。
      - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してカレントプロセス優先度を設定。
      - CPU affinity 設定ユーティリティも追加（最初の N コアに固定）。
      - 権限不足や未対応 OS での失敗は警告ログを出力してフォールバック。

### Changed
- 環境/設定の堅牢化
  - Settings クラスに多数の入力検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正な値は ValueError を投げることで早期に検出。
  - paper_trading 用 SQLite パスを Settings で容易に取得できるプロパティを追加。

- DB 初期化/接続の扱い
  - monitoring 系の起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - ExecutionEngine 起動時に paper_trading 環境で DB を分離する挙動を明確化。

### Fixed
- .env パーサの不具合回避（推測）
  - 無効な行やコメント、引用符付き文字列内のエスケープなどを正しく処理することで .env の読み込みミスを低減。
- ポーリング間隔処理の堅牢化
  - MONITOR_POLL_INTERVAL の値が 0 以下または非整数のときに time.sleep での例外を防ぐため、デフォルトへフォールバックし警告を出力するように修正。
- 研究・解析系の境界処理
  - ファクター計算やボラティリティ計算でウィンドウ不足時の None ハンドリングやカウントチェックを導入（cnt_200 / cnt_atr 等）。
  - calc_forward_returns の horizons 入力検証を追加（正の整数かつ <= 252 の制限）。

### Security
- OpenAI API キーの要求を明示（news_nlp）。キー未設定時は ValueError を送出して安全性を確保。

---

## [0.1.0] - 2026-04-17

初回公開リリース（推定）。上記 Unreleased の主要機能群を含む初期版リリースとしてタグ付け想定。

### Added
- 基本パッケージ構成とバージョニング（kabusys.__version__ = 0.1.0）
- 実行・監視スクリプト（run_execution, run_monitoring）
- ポートフォリオ構築モジュール（selection, weighting, position sizing, sector cap, regime multiplier）
- 研究用モジュール（ファクター計算・forward returns・IC・統計サマリ）
- AI ニュース NLP スコアリング基盤（OpenAI 連携の設計実装）
- Paper Trading 検証レポート CLI（paper_verification_report）
- 設定管理（.env 自動読み込み、堅牢なパース）
- プロセス優先度 / CPU affinity ユーティリティ
- DuckDB / SQLite を用いたデータアクセス基盤

### Changed
- 環境変数のバリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）
- Paper Trading 環境と本番 DB の分離を明確化

### Fixed
- 各種境界条件のハンドリングを強化（ウィンドウ不足、NULL 値、空のリスト等）

---

注記:
- この CHANGELOG はコード内のドキュメント文字列・コメント・命名・既知の TODO から推測して作成しています。実際のコミット履歴に基づく正確な差分ではありません。必要であれば、実際の Git コミットログを元に正式な履歴を作成します。