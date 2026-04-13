CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
セマンティックバージョニングを採用しています。

Unreleased
----------

変更予定・既知の改善点 / 注意点（コードコメントや実装から推測した未完・改善候補）

- Added
  - AIニューススコアリングの堅牢化: ai/news_nlp.py のスコア書き込み処理について部分的な失敗を回避するための「部分置換（DELETE → INSERT）」方針は実装方針として明記されている。今後、部分失敗時のリトライ/ロールバック/監査ログの追加や、OpenAI レスポンスのさらに詳細な検証を行う予定。
  - position_sizing の単元株（lot_size）を銘柄別に管理する拡張（コメントで TODO）。将来的に stocks マスタから lot_size を読み込む設計へ拡張予定。
  - apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価）の導入検討。現在は price が欠損するとエクスポージャーを過少評価する可能性がある旨がコメントで示されている。

- Fixed / Improved
  - 一部の環境依存処理（プロセス優先度 / CPU affinity）は既に警告ログを出して安全にスキップする実装。今後、より詳細な権限チェックやユーザ向けドキュメントの追記を行う予定。

- Security
  - OpenAI API キー未設定時は score_news が ValueError を投げる設計。運用上は API キー管理方法の追記や秘密情報の取り扱いポリシーを整備予定。

0.1.0 — 2026-04-13
------------------

初回リリース — リポジトリの主要機能を実装したバージョン（コード内容から推測）

- Added
  - 基本情報
    - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
    - パッケージ公開用の __all__ を定義（data, strategy, execution, monitoring）。

  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用（本番 DB と分離）。
      - BrokerClientFactory を経由してブローカークライアントを生成。
      - OrderRepository / OrderManager / Reconciler / RiskManager の組み立てと ExecutionEngine.run_session 呼び出し。
      - デフォルトでプロセス優先度を "high" に設定する処理を実行開始時に行う。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用 DB は環境にかかわらず production の sqlite_path を使用（コメント記載）。
      - プロセス優先度を "high" に設定してから監視を開始。
      - check_once の例外はログに記録してポーリングを継続する堅牢化。

  - 設定管理
    - config.py: 環境変数/.env 管理を実装。
      - .git または pyproject.toml を手掛かりにプロジェクトルートを探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パースは export 形式・クォート・エスケープ・インラインコメントに対応する堅牢な実装。
      - Settings クラスを提供し、各種設定値（API トークン、DB パス、paper_trading 用パス、閾値、PID/kill-flag パスなど）をプロパティとして取得可能。
      - KABUSYS_ENV / LOG_LEVEL 等の値検証を行い不正値では ValueError を送出。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。

  - 監視・ユーティリティ
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（Windows / POSIX）と CPU affinity を設定するユーティリティを実装。
      - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢化。

  - Paper Trading ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
      - CLI から期間指定（--from / --to / --db）が可能。
      - システム稼働率（system_status）、注文成功率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（p95 等）を集計してレポート出力。
      - Pass/Fail 判定を行う閾値を定義（稼働率 99%、成功率 90% 等）。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順で上位 N を選択、タイブレークは signal_rank。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。全スコアが 0 の場合は等配分にフォールバックして WARN を出す。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限を適用して候補をフィルタ。
      - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。lot_size による丸め、aggregate cap によるスケールダウンロジックを含む。
      - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト見積りと調整処理を実装。
      - コメントで将来の拡張点 (銘柄別 lot_size) を明記。

  - リサーチ / ファクター計算
    - research/factor_research.py
      - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、per、roe 等）を計算。
      - 長期移動平均やATRなどのウィンドウ処理を DuckDB のウィンドウ関数で実装。
    - research/feature_exploration.py
      - calc_forward_returns: 将来リターン（複数ホライズン）を計算。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
      - factor_summary / rank: 基本統計量・ランク変換ユーティリティを実装。
    - research/__init__.py で主要関数をエクスポート。

  - AI ニュース NLP（OpenAI 統合）
    - ai/news_nlp.py
      - raw_news を銘柄ごとに集約し、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出する処理を実装。
      - バッチサイズ、記事上限、文字数上限、リトライ（429/5xx/ネットワーク断）、指数バックオフ、JSON Mode での厳密なレスポンス検証、スコアの ±1.0 クリップを行う設計。
      - タイムウィンドウの計算は calc_news_window(target_date) で行い、ルックアヘッドバイアスを避けるために datetime.today() に依存しない実装。
      - OpenAI API キー未設定時は明示的にエラーを出力（ValueError）。

  - DB / クエリ関連
    - DuckDB と SQLite の両方を利用する設計を採用。実行系・監視系でそれぞれ適切な DB パス・接続を行う。
    - monitoring_db.init_monitoring_db を起動時に呼び出して監視用テーブルの存在を保証（冪等）。

- Changed
  - 設定ファイルの自動ロード順序を明確化: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
  - 多くの CLI/起動スクリプトで logging.basicConfig(level=INFO) を初期化。

- Fixed
  - .env 読み込みの失敗時に warnings.warn して安全に動作継続するよう変更。
  - process_priority/set_cpu_affinity は権限不足や未実装メソッドに対してログを残してスキップするよう堅牢化。

- Removed
  - （特になし／初版のため削除履歴なし）

- Security
  - OpenAI キーや各種シークレットは環境変数経由で取得。未設定時は明示的にエラーを出すことで安全側へ倒す設計。

注記 / 既知の制約
-----------------

- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるというコメントが残っている。将来、前日終値や取得原価等のフォールバックを検討する必要あり。
- position_sizing: 銘柄別の単元管理（lot_size マップ）への拡張がコメントで示唆されている。
- ai/news_nlp: DuckDB への書き込みは「影響範囲を限定した部分置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）」方針を採るが、部分失敗時のオペレーション（リトライや通知）をさらに強化する余地がある。
- DuckDB executemany の制約（params が空だと問題になる）に配慮した実装上の注意がコードコメントにある。運用での注意事項をドキュメント化することを推奨。

参考
----

- 本 CHANGELOG はソースコード中のコメント・実装の振る舞いから推測してまとめたものです。実際のコミット履歴が存在する場合はそちらを優先してください。