# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。

なお、本 CHANGELOG は提示されたコードベースから推測して作成しています。実際のコミット履歴や日付が存在しないため、主な追加機能・改善点・修正点を機能単位でまとめています。

## [Unreleased]

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境変数 KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite DB を使用し、MockBrokerClient を利用する構成をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- 設定管理
  - config.py: プロジェクトルートを自動検出して .env / .env.local を環境変数にロードする仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。.env のパースロジックを強化（export プレフィックス、クォート内のエスケープ、インラインコメント処理など）。Settings クラスで多数の設定プロパティを提供（DB パス、paper_trading DB、PID ファイルパス、監視閾値、env/log_level 検証、PAPER_FILL_MODE の検証など）。

- 監視（Monitoring）
  - monitoring DB 初期化ユーティリティを呼び出す導線を run_* スクリプトへ追加（init_monitoring_db 呼び出しにより監視テーブルの存在を保証）。

- Execution / リスク管理
  - run_execution.py で BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッションを実行する流れを実装。
  - RiskManager の設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連, initial_portfolio_value）を明示。

- Portfolio 構築
  - portfolio/portfolio_builder.py: 候補銘柄選定（スコア降順、同点時の tie-break）、等金額・スコア加重配分関数を追加。スコア合計が 0 の場合のフォールバック挙動を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装（未知のレジームはフォールバックし警告を出力）。
  - portfolio/position_sizing.py: 各配分方法（risk_based / equal / score）に沿った発注株数算出、単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash を超えた場合のスケールダウン）および cost_buffer の考慮、端数処理ロジックを追加。

- 研究 / ファクター計算
  - research/factor_research.py: DuckDB を用いたモメンタム・ボラティリティ・バリューの計算関数を追加（mom_1m/3m/6m、ma200 偏差、ATR20、avg_turnover、PER/ROE など）。不足データ時の None ハンドリングやウィンドウスキャン範囲の考慮を実装。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、rank ユーティリティを実装。ties を平均ランクで扱う仕様。

- AI ニューススコアリング
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理を実装。タイムウィンドウ計算、銘柄ごとの記事集約、バッチ（最大 20 銘柄）送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードに対する置換）などを設計に反映。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を出力。期間指定オプション（--from / --to / --db）を提供。DB のテーブル欠如に対しては安全に N/A / 0 を扱う。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム差（Windows / POSIX）を吸収したプロセス優先度設定関数 set_process_priority と CPU affinity 設定関数 set_cpu_affinity を追加。権限不足や未対応 OS の場合は警告でスキップする堅牢な実装。

### Changed
- ロガー出力の明確化
  - 各モジュールで起動時・主要処理での logger.info / logger.debug を追加し、実行時のトラブルシュートを容易化。

- DB 接続方針の明示
  - run_monitoring.py は監視用途で本番 sqlite_path を使用する（環境に依存しない）旨を明示。
  - run_execution.py は paper_trading 環境のとき paper_sqlite_path を使って本番データと分離。

- .env ロードの優先順位を明記
  - OS 環境変数 > .env.local > .env の順で読み込み。OS 環境変数は保護され自動上書きを防止。

### Fixed / Robustness
- 環境変数の検証強化
  - Settings: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値検証を追加し、不正値時に ValueError を送出。
  - MONITOR_POLL_INTERVAL のパースで 0 以下や非整数が指定された場合のフォールバック（デフォルト 60 秒）を実装し警告を出力。

- エラー耐性の向上
  - run_monitoring.py のポーリングループ内で check_once() の例外を捕捉してログ出力後に次のポーリングを継続するように変更（1回の例外でループ全体が停止しない）。
  - ai/news_nlp の API 呼び出しで失敗時はリトライとフォールバック（フェイルセーフで処理継続）を設計。

- SQL/集計処理の安全化
  - tools/paper_verification_report.py: テーブルが存在しない場合の sqlite3.OperationalError を捕捉してデフォルト値にフォールバックするように実装。

### Documentation / Comments
- 各モジュールに設計方針・アルゴリズム説明の docstring を充実させ、将来の保守や拡張を容易にする注釈を追加。

## [0.1.0] - 2026-04-13

初期リリース相当と推測される状態を以下にまとめます（上記 Unreleased の内容の多くはこのバージョンに含まれる想定です）。

### Added
- 基本機能の提供
  - 自動売買システムの主要コンポーネント（ExecutionEngine 起動フロー、Order 管理、RiskManager、Reconciler、BrokerFactory 連携）。
  - 監視用 SystemMonitor の起動ループ（監視ログ収集・記録）。
  - Portfolio 構築パイプライン（候補選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数）。
  - 研究（research）モジュール（モメンタム/ボラティリティ/バリュー計算、将来リターン、IC、ファクター統計）。
  - AI ニューススコアリング（OpenAI を用いた銘柄別センチメントスコア付与。
  - Paper Trading 向け検証ツール（paper_verification_report）。
  - 環境設定管理（.env ロード・Settings クラス）。
  - プロセス優先度・CPU affinity ユーティリティ。

### Changed / Fixed
- 初期リリース相当の安定化措置（入力検証、エラー捕捉、フォールバック、ログ出力の改善など）。

---

保持したい点、実際のバージョン/日付情報の追加、あるいは特定のファイルや機能に対するより詳細な変更理由（設計意図や既知の制限事項）を追記したい場合は、対象箇所を指定してください。必要に応じてバージョンごとにより細かい変更分（関数単位の修正や既知バグ）を推測して追加します。