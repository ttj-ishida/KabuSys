CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
タグ付け / リリース日付はコード内容および現時点の推察に基づいています。

フォーマット
------------
- Unreleased: 今後の変更用プレースホルダ
- 各リリースセクションは日付付きで主要な追加・変更点を分類しています（Added / Changed / Fixed / Notes など）

Unreleased
----------
- 今後の機能追加・改善を記載します。

[0.1.0] - 2026-04-12
--------------------

Added
- 基本パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 実行系および監視の起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。設定に応じて paper_trading モード時は専用の SQLite DB を使用し、本番 DB と分離して動作。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - RiskManager の初期構成値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を明示。
    - リスクマネージャ初期資金は broker.get_available_cash() から取得。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production 相当の sqlite_path を使用（監視データを一元管理）。
    - プロセス優先度を起動時に "high" に設定。

- 設定 / 環境変数管理
  - config.Settings を導入し、環境変数経由で各種設定値を取得可能に。
    - 自動 .env ロード機構を導入（.env, .env.local）: プロジェクトルート（.git または pyproject.toml）を基準に探索。
    - OS 環境変数を保護する protected 機能、override による上書き制御を実装。
    - .env パーサは export KEY=val、クォート文字のエスケープ、インラインコメントの取り扱いなどに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。
    - 各種設定プロパティを実装:
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）
      - PID / KILL フラグパス、閾値（CPU/MEM/DISK）、ログレベル検証、環境値検証（development/paper_trading/live）など。

- 監視データベース初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの冪等初期化を実施（Execution / Monitoring 起動時に自動保証）。

- ポートフォリオ構築・サイズ算出・リスク調整
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア全てが 0.0 の場合は等金額配分へフォールバックし warning を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき候補をフィルタリング。既存保有からセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック、warning）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）ごとに発注株数を計算する強力なユーティリティを追加。
      - 単元株（lot_size）丸め、max_position_pct による per-stock 上限、max_utilization による全体上限、cost_buffer による保守的なコスト見積りを実装。
      - aggregate cap 超過時は総コストに応じたスケールダウン処理と端数の lot_size 単位での再配分ロジックを実装（再現性のため stable sort）。
      - risk_based では stop_loss_pct を使ったポジションサイズ算出。

- 研究（research）モジュール
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高変化率を計算。
    - calc_value: raw_financials から EPS/ROE を用いた PER/ROE を計算（target_date 以前の最新財務データを使用）。
    - 各関数は DuckDB 接続を受け prices_daily / raw_financials を参照し、データ不足時には None を返す設計。
  - research.feature_exploration:
    - calc_forward_returns: 翌日/翌週/翌月など将来リターンをまとめて取得可能。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（<3 件）なら None。
    - rank / factor_summary: ランク変換とファクターの統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージの __all__ を整備し、zscore_normalize（kabusys.data.stats 依存）等と合わせてエクスポート。

- AI ニュース NLP モジュール
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）へ送りセンチメントスコアを ai_scores へ書き込むワークフローを追加。
    - ニュース収集ウィンドウの算出（JST ベース: 前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - 記事集約・文字数 / 記事数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE（20）銘柄ごとのバッチ送信、JSON Mode を期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx について指数バックオフでリトライ（上限 _MAX_RETRIES）。
    - レスポンス検証、スコアの ±1.0 クリッピング、部分成功時のテーブル更新戦略（DELETE 範囲を絞ってから INSERT）により冪等性と被害最小化を図る。
    - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX(Linux, Darwin, FreeBSD) を吸収して nice/priority を設定。権限不足や未対応環境は warning 出力してスキップ。
    - set_cpu_affinity: 最初の N コアに固定する機能（None で無効）。不正引数や権限不足は warning でスキップ。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成 CLI を追加（--from / --to / --db オプション）。
    - 検証指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数など。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）し、PASS/FAIL 判定を出力。
    - DB テーブルが存在しない場合や OperationalError のハンドリングを行い、欠損データに寛容に動作する。

Changed
- （初版のため履歴なし）今後のリリースで差分を記載予定。

Fixed
- .env ファイルパーサの堅牢化（クォート内エスケープ、インラインコメントの取り扱い、export プレフィックス対応等）。
- 各種関数でのゼロ除算・欠損データに対する保護（例: momentum / volatility / value の計算で不足データは None を返す）。

Notes
- データベース
  - DuckDB を分析用途（prices_daily, raw_financials 等）に使用。実行時は settings.duckdb_path を参照。
  - SQLite は監視・注文履歴（monitoring.db / paper_trading.db）に使用。paper_trading モード時は PAPER_TRADING_SQLITE_PATH で本番 DB と分離。
- ロギング
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を使うことで INFO レベルのログを標準出力に出すようになっている。Settings.log_level による柔軟なログレベル切替は今後の起動オプションで利用可能。
- フェイルセーフ設計
  - OpenAI など外部 API 呼び出しは失敗時にスキップ／部分更新で他レコードを保護する設計。
  - 権限不足でのプロセス優先度変更や CPU affinity 設定は警告ログを出して安全にスキップ。

今後の予定（示唆）
- 単体テスト用の DI / モック拡張（現状は Settings による環境依存を .env 制御で回避）。
- position_sizing の lot_size を銘柄別に持てるよう stocks マスタ連携への拡張。
- AI モジュールの結果保存・再実行性向上、OpenAI の JSON Mode レスポンスパース強化。
- 実行時のログレベル・メトリクス出力の改善（Prometheus などへの統合検討）。

ライセンス・貢献
- 本 CHANGELOG は提供されたコードベースから推測して作成したドキュメントです。追加の変更履歴やリリースノートは実際のコミットログ・タグ付けに基づいて更新してください。