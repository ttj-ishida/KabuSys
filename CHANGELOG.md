# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、以下はコードベースの内容から推測して作成した初回リリース向けの変更履歴です（実装コメントやドキュメント文字列に基づいて要点をまとめています）。

## [Unreleased]
- （現在未リリースの変更はありません。）

## [0.1.0] - 2026-04-16
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

### Added
- コアパッケージ初期構成
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV が `paper_trading` の場合、専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用する処理を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行スレッド管理を実装。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止、実行中 PID ファイル (data/execution.pid) の参照。
    - RiskManager のデフォルト構成（最大ポジション比率、利用率、リミット、サーキットブレーカー等）を設定。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイル検出によるループ終了処理、例外発生時のロギングとリトライ継続。

- 設定管理
  - config.py
    - .env/.env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env パーサーは export プレフィックス、クォート、インラインコメント、エスケープに対応。
    - 環境変数の保護（OS 環境を上書きしない挙動）をサポート。
    - Settings クラスを通じたアプリ設定 API（J-Quants、kabuAPI、LINE、データベース、監視閾値、ログ設定、環境判定など）。
    - 各種バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- Paper Trading 向けユーティリティ
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - コマンドライン引数で期間指定 (--from, --to)、DB パス指定 (--db) に対応。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標集計と PASS/FAIL 判定用閾値を実装（閾値はファイル内定義）。
    - SQLite のテーブル存在チェックや例外を考慮した頑健な実行。

- ポートフォリオ構築・リスク調整・ポジションサイズ計算（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て0の際のフォールバック挙動（等分配）と警告ログ。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック (apply_sector_cap) を実装。既存保有のセクター別エクスポージャ計算と新規候補の除外ロジックを提供。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出を実装。
    - 1銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）、lot_size（単元丸め）、cost_buffer を考慮した保守的な配分ロジック。
    - スケーリング時の端数配分アルゴリズム実装（lot_size 単位で残余を再配分）。

- 研究（research）モジュール
  - research/factor_research.py
    - Momentum, Volatility, Value ファクター計算を DuckDB 経由で実装（prices_daily / raw_financials テーブル参照）。
    - mom_1m/3m/6m、MA200乖離、ATR20、相対ATR、20日平均売買代金、出来高比率、PER/ROE などを算出。
    - データ不足時の None ハンドリング、計算ウィンドウの説明・設計意図を明記。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリー（factor_summary）を実装。
    - Spearman ランク相関（IC）計算、ランク処理（同順位は平均ランク）を実装（丸め対策含む）。
  - research パッケージ初期エクスポートを追加（zscore_normalize を data.stats から再エクスポート）。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを生成し ai_scores テーブルへ書き込む設計を追加。
    - バッチ処理（最大 20 銘柄 / コール）、JSON Mode、応答バリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライなどの方針を実装。
    - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 → UTC に変換）関数を提供。
    - API キー解決（引数 > 環境変数 OPENAI_API_KEY）と未設定時のエラー。

- ユーティリティ
  - utils/process_priority.py
    - Windows (psutil の HIGH_PRIORITY_CLASS 等) と POSIX (nice 値) を吸収してカレントプロセスの優先度設定を行う関数を実装（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- DB 初期化ユーティリティ呼び出し
  - monitoring.monitoring_db.init_monitoring_db が run 系スクリプトから呼ばれ、監視用テーブルが存在することを保証（冪等処理）。

### Changed
- （初回リリースのため変更記録なし）

### Fixed
- （初回リリースのため修正記録なし）

### Security
- OpenAI API キーや各種シークレットは Settings/環境変数経由で取得し、.env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。  
  ただし、本リリースでは秘密管理・暗号化までは実装していないため運用上は OS 環境変数やシークレットマネージャの併用を推奨。

### Notes / Known limitations（コードコメントより推測）
- ai/news_nlp.score_news: ファイル末尾が途中で切れているように見える（本 changelog 作成時点のコード断片）。実装は設計を含むが、完全な書き込み処理・実行ループが未確認。
- position_sizing の価格欠損（price が 0.0）時の挙動について TODO コメントあり（前日終値等のフォールバック未実装）。
- .env パーサーはかなり堅牢だが、特殊ケースの完全網羅は要検証（複雑なクォートや改行を含む値など）。
- research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存。実データパイプラインとの統合テストが必要。

---

参考: 各モジュールの詳細はソース内の docstring / コメントを参照してください。必要であれば、各機能ごとにリリースノートを分割してより細かく記載することも可能です。どのレベルで詳細化するか指定してください。