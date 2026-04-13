# Changelog

すべての変更は Keep a Changelog のフォーマットに従って記載しています。Semantic Versioning に準拠しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-13

### Added
- プロジェクト初期リリース: 基本機能群を実装。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0" を設定。
    - パッケージの公開 API を __all__ で整理。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントルールに対応）。
  - 環境変数の上書きルール:
    - .env は既存環境変数を上書きせず未設定キーのみセット
    - .env.local は override=True で OS 環境変数を保護しつつ上書き可能
  - Settings クラスを実装し、様々な設定値をプロパティで提供（duckdb/sqlite パス・PID/kill フラグパス・閾値・API トークン等）。
  - 必須変数未設定時に ValueError を投げる _require ユーティリティを追加。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等のバリデーションを実装（不正値は例外を投げる／警告する）。

- 実行 / 監視スクリプト
  - run_execution.py（src/kabusys/run_execution.py）
    - ExecutionEngine 起動エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - 監視テーブルを冪等に初期化（init_monitoring_db）。
    - DuckDB 接続を生成して ExecutionEngine に渡す。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager（RiskConfig）／Reconciler の組み立て。
    - RiskConfig のデフォルト値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定。
    - ExecutionEngine.run_session() を呼び出し実行。
    - プロセス優先度を最初に "high" に設定（set_process_priority）。

  - run_monitoring.py（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト。
    - 監視は環境に依存せず本番 sqlite_path を使用（監視データは常に本番 DB に記録）。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告を出力。
    - プロセス優先度を "high" に設定。
    - check_once() の例外はキャッチしてログ出力し次ループを継続。KeyboardInterrupt で優雅に終了。

- 監視 DB 初期化ユーティリティ（参照: kabusys.monitoring.monitoring_db）
  - run_* スクリプトから init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

- プロセス優先度 / CPU 固定ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装し、Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) を実装。最初の N コアに固定する機能を提供（cpu_count=None で何もしない）。権限不足や未サポート環境では警告を出力してスキップ。
  - 不正パラメータや未対応 OS の扱いを明示。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同スコアは signal_rank でタイブレーク）で上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有を基にセクター集中制限（max_sector_pct）を適用し、超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックして警告。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた株数計算を実装。
    - risk_based: 損切り率 stop_loss_pct と risk_pct に基づく理論株数算出。
    - equal/score: ウェイトに基づく割当を計算。
    - lot_size による単元丸め、max_position_pct に基づく per-stock cap、available_cash に対する aggregate cap によるスケールダウン（残差処理で lot 単位での追加配分ロジックあり）。
    - cost_buffer を導入し手数料・スリッページを保守的に見積もる。
  - モジュールエクスポートを __all__ で整理。

- 研究・ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を DuckDB の prices_daily を用いて計算。十分な履歴がない場合は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL の伝播を考慮した true_range 計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0 または NULL の場合 PER は None）。
    - 全て DuckDB 接続を受け、prices_daily / raw_financials を参照し外部 API にはアクセスしない設計。
  - feature_exploration.py
    - calc_forward_returns: 指定 horizon 列の将来リターン（fwd_1d, fwd_5d, fwd_21d 等）を一括クエリで取得。horizons のバリデーションを実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。データ不足（有効ペア < 3）で None を返す。
    - rank / factor_summary: 同順位の平均ランク割当とカラム別統計（count/mean/std/min/max/median）を実装。
  - research.__init__ で zscore_normalize（kabusys.data.stats）と合わせて公開。

- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から記事を集約し、OpenAI API（gpt-4o-mini）で銘柄ごとの sentiment を -1.0〜1.0 のスコアで算出して ai_scores テーブルへ書き込む処理を実装。
  - 設計上のポイント:
    - ニュース時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換したウィンドウ）。
    - 1 銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大を抑制。
    - 最大バッチサイズ _BATCH_SIZE（20 銘柄）で API に送信、JSON Mode を期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（_MAX_RETRIES / _RETRY_BASE_SECONDS）。
    - レスポンス検証（JSON フォーマット、results キー、既知コード、数値スコア）とスコアの ±1.0 クリップ。
    - API キーが未設定の場合は ValueError を送出。
    - フェイルセーフ: API 部分で失敗した場合も他銘柄の処理を継続できる設計。
    - ai_scores 置換は影響範囲を code で限定して安全に実行（部分失敗時に既存スコアを保護）。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - paper_trading DB（デフォルト data/paper_trading.db）を読み込み、以下をレポートする CLI ツールを実装:
    - システム安定性（総ポーリング数、エラー数、稼働率）
    - 注文成功率（Created / Filled / Sent 件数、成功率）
    - シグナル精度（送信率、リスク却下数）
    - API レイテンシ（平均 / 最大 / P95）
  - 判定基準（閾値）を定義して PASS/FAIL を出力:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - --from / --to / --db CLI オプションをサポート。日付フィルタは ISO8601 UTC 範囲に変換してクエリに適用。
  - 空データやテーブルが存在しない場合のフォールバック（OperationalError を捕捉して N/A や 0 を出力）。

### Security
- 本リリースでは特段のセキュリティ修正は含まれないが、OpenAI API キーの取り扱いは環境変数経由を推奨。APIキー未設定時は明示的な例外を発生させることで誤動作を防止。

---

注:
- 上記の CHANGELOG は提供されたコードベースの内容から推測して作成したもので、実際のリリースノートに含めるべき細部（例えば外部依存バージョン、マイグレーション手順、テストの有無など）はプロジェクトの運用ポリシーに応じて追記してください。必要であれば、各ファイルごとの変更点をさらに細かく分割した詳細な履歴も作成できます。