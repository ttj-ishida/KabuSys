CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
（今後の予定・既知の改善点）
- ai/news_nlp の記事取得パイプライン改善:
  - _fetch_articles 等の集約処理でのエラー処理強化、トークン削減ロジック（記事トリム）をより堅牢にする予定。
- 価格フォールバック:
  - position_sizing / apply_sector_cap における価格欠損時のフォールバック（前日終値や取得原価）を追加予定。
- 単元株対応の拡張:
  - lot_size を銘柄別に設定できるよう stocks マスタの導入検討。
- テスト整備:
  - research / portfolio / ai モジュール向けのユニットテスト拡充。
- ドキュメント:
  - PortfolioConstruction.md / StrategyModel.md で参照している設計文書のリンクを README に統合予定。

0.1.0 - 2026-04-17
-----------------
Added
- コア機能
  - 初期リリース。日本株自動売買システム "KabuSys" の基礎機能群を追加。
  - バージョニング: kabusys.__version__ = "0.1.0"。
- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パーサ実装: コメント行、export 前置、シングル／ダブルクォート、エスケープ、インラインコメント処理をサポート。
  - 環境変数必須チェック関数 _require を実装し、Settings クラスから安全に設定値を取得可能に。
  - 各種設定プロパティを実装（DB パス、PID ファイル、監視しきい値、PAPER_FILL_MODE のバリデーション等）。
- 実行 / 監視スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) 検知で安全停止。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用して状態を記録。
    - プロセス優先度を起動時に設定（high）。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db により、接続時に監視用テーブルの存在を保証（冪等）。
- 実行コンポーネント
  - execution パッケージ（EngineConfig / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager）を組み込み（エンジン構成とデフォルトリスク設定を含む）。
  - RiskConfig によるデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- Portfolio（銘柄選定・配分）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て 0 の場合はフォールバックで等配分）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限ロジック（既存保有を基に当日売却予定銘柄を除外可、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知時フォールバック警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数決定ロジック。
    - lot_size（単元株）考慮、per-position 上限、aggregate cap スケーリング（切り捨て＋再配分アルゴリズム）実装。
    - cost_buffer による手数料・スリッページ見積考慮。
- Research（因子・探索）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB 上で計算。
    - calc_volatility: ATR20 / 相対 ATR / 20日平均売買代金 / 出来高比率を計算。
    - calc_value: EPS などを用いた PER / ROE の計算（raw_financials の最新レコード取得ロジック含む）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。
    - calc_ic: スピアマンランク相関による IC 計算（データ不足時は None）。
    - factor_summary / rank: 基本統計量と順位化ユーティリティを提供。
  - research パッケージは DuckDB 接続を前提に、外部 API へは依存しない設計。
- AI ニュース NLP（ai.news_nlp）
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリング機能を追加。
  - 機能:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で raw_news を集約。
    - 銘柄ごとに記事をトリム（最大記事数・文字数）してバッチ送信（最大 20 銘柄/回）。
    - 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証とスコアの ±1.0 クリップ。
    - 成功分のみ ai_scores テーブルを置換的に更新（部分失敗での既存スコア保護）。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ、リスク却下数。
    - パス/フェイル基準を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200 ms）。
    - コマンドライン引数で期間フィルタ（--from/--to）と DB パス（--db）を指定可能。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows と POSIX を吸収してプロセス優先度（high/normal/low）を設定。権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を提供（権限不足時は警告を出してスキップ）。
  - utils パッケージを整備して共通処理を提供。
- パッケージ公開面
  - 各サブパッケージに __all__ / エクスポートを設定（portfolio, research など）。

Changed
- ログ設定
  - run_* スクリプトで logging.basicConfig(level=INFO) によるデフォルトのログレベルを設定。
- DB ハンドリング
  - monitoring の初期化を冪等にして任意の環境で安全に呼べるようにした（paper_trading 向け DB 分離を含む）。

Fixed
- 設定パースの堅牢化
  - .env の引号付き値でのバックスラッシュエスケープ処理や、クォートなしのインラインコメント検出を修正・強化。
- モニターポーリング間隔の扱い
  - MONITOR_POLL_INTERVAL が不正または 0 以下の値のときにデフォルトにフォールバックして ValueError を避けるようにした（警告出力付き）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用（未設定時は ValueError を送出）。キーのハードコーディングは行っていない。

Notes / Known issues
- ai/news_nlp の記事フェッチ周りの実装（fetch 部分）は複雑であり、スループットと API レート制限のバランスに注意が必要。部分失敗時のロギングや再試行ポリシーは現状の実装でカバーするが、運用での観察を推奨します。
- position_sizing の価格欠損時の扱い（price_map に価格が無い/0.0 の場合）は TODO コメントを残しており、将来的にフォールバック価格を追加する予定です。
- set_cpu_affinity / set_process_priority は権限依存（root / 管理者）となるため、実行環境によっては期待どおりに動作しない場合があります。権限不足時は警告ログが出力され、処理は継続します。

以上。