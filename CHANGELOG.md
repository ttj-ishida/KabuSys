# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠し、セマンティックバージョニングを採用します。日付はリリース日を示します。

## [0.1.0] - 2026-04-12

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を追加。
  - パッケージバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数 / .env ファイルの自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルートを `.git` または `pyproject.toml` を起点に探索し、.env/.env.local を読み込む（自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどを考慮して実装。
    - 必須環境変数未設定時は明確なエラーメッセージを送出する `_require()` を提供。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、Paper Trading 関連設定、監視閾値、PID/KILL フラグ設定、環境判定等）。
    - PAPER_FILL_MODE の検証（有効値: "instant" | "partial" | "never" | "reject"）とバリデーションを実装。

- 実行エンジン関連
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を設定（utils/process_priority）。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - ブローカークライアントのファクトリを利用して実行（BrokerClientFactory）。
    - OrderRepository, OrderManager, RiskManager（RiskConfig含む）, Reconciler を組み立て、ExecutionEngine を起動するワークフローを実装。
    - 実行後に DB 接続（SQLite / DuckDB）をクローズ。

- 監視関連
  - SystemMonitor ポーリング起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0以下や非整数）は警告を出しデフォルトにフォールバック。
    - 監視（monitoring）は環境に関わらず本番用 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を High に設定、SQLite / DuckDB 接続を作成し、ポーリングループ内で monitor.check_once() を定期実行。例外はログに記録してループを継続。KeyboardInterrupt で優雅に終了。

- 監査・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間（--from / --to / 環境変数で DB パス指定可能）に対してシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を算出してレポート出力。
    - パス/フェイル判定の閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - SQLite のテーブル欠損に対しては安全にデフォルト値を返す実装（OperationalError をキャッチ）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（各重み 1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター別時価評価から上限超過セクターをブロックし、新規候補を除外（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じて発注株数を算出（"risk_based", "equal", "score" をサポート）。
    - risk_based: 許容リスク率と stop_loss を用いて理論株数算出、単元（lot_size）で丸め。
    - equal/score: 重みと max_utilization を用いた割付。per-position 上限や aggregate cap（available_cash）に基づくスケーリングを実装。
    - cost_buffer による保守的なコスト見積り、スケールダウン時の端数処理（lot 単位での追加配分）を実装。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, Darwin, FreeBSD）を吸収して優先度設定を行う set_process_priority。
    - CPU 固定用の set_cpu_affinity を実装（1 以上の cpu_count 検証、利用可能コア数を超える場合は全コア使用）。
    - 権限不足や未実装 API に対しては警告を出して安全にスキップ。

- リサーチ / ファクター
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率 を計算（DuckDB のウィンドウ関数を利用）。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を適切に扱う）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（target_date 以前の最新財務レコードを採用）。
  - 特徴量探索ユーティリティを追加（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（LEAD を利用）。horizons の検証を実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。データ不足（有効レコード < 3）で None を返す。
    - rank / factor_summary: ランク付け（同順位の平均ランク）および各種基本統計量（count/mean/std/min/max/median）を計算。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコアリングし ai_scores に書き込むモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
    - 銘柄ごとに記事を集約し、最大 20 銘柄 / チャンクで API 呼び出し。記事・文字数の上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レスポンス検証、スコアの ±1.0 クリップ、429 / ネットワーク断 / 5xx に対する指数バックオフリトライを実装（最大 3 回）。
    - 出力 JSON の厳密な形式を想定（{"results":[{"code":"XXXX","score":0.0},...] }）。
    - OpenAI の API キーの解決（引数 > 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- パッケージ公開 API
  - research と portfolio モジュールの __all__ を整備し、主要関数を外部からインポート可能にした（src/kabusys/research/__init__.py、src/kabusys/portfolio/__init__.py）。

### Changed
- なし（初期リリースのため変更履歴はありません）。

### Fixed
- なし（初期リリース）。

### Known issues / Notes
- 一部の TODO / 注意点を残しています（今後の改善ポイント）。
  - portfolio/risk_adjustment.apply_sector_cap:
    - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる旨の注記。前日終値や取得原価でのフォールバックを将来検討。
  - position_sizing:
    - lot_size は全銘柄共通で固定（現在 100 を想定）。将来的に銘柄別 lot_map に拡張予定。
  - DuckDB の executemany に関する注意: ai_news 処理で params が空だとエラーになる点に配慮した実装（実行前に空チェック）。
  - news_nlp.score_news:
    - OpenAI 呼び出しの失敗時はフェイルセーフとしてスキップして継続する設計。ただし部分的失敗時の運用方針（再試行/通知）を検討の余地あり。
  - run_monitoring:
    - MONITOR_POLL_INTERVAL に 0 や負値、非整数が指定された場合は警告ログを出して 60 秒にフォールバック（time.sleep に渡すと ValueError になることを回避）。

### Security
- OpenAI / 外部 API キーや機密情報は環境変数を前提としており、.env の自動読み込みは OS 環境変数を保護する仕組み（protected）で実装されています。
- 必須の機密環境変数が未設定の場合は早期にエラーを発生させることで不完全な構成での稼働を防止。

---

今後のリリースでは以下を優先的な改良候補として想定しています:
- Unit / integration テストの追加と CI パイプライン整備
- broker client と ExecutionEngine の詳細実装・フェイルオーバー強化
- ニュース NLP の結果保存戦略（部分失敗復旧・通知）
- 銘柄ごとの lot_size 対応、価格フォールバックロジックの強化
- 設定やログ周りのドキュメント整備（README / Operation Guide）

以上。追加でリリースノートの分割（Unreleased / 次バージョン案）や日付の調整などを希望される場合は指示ください。