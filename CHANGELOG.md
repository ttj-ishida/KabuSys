# CHANGELOG

すべての注目すべき変更を記載します。形式は「Keep a Changelog」に準拠しています。  
以下の変更内容は提供されたコードベースから推測して記載しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。システム全体のコア機能（実行エンジン・監視・設定管理・ポートフォリオ構築・リサーチ・AI ニュース NLP・ユーティリティ・検証ツール等）を含みます。

### Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として追加（src/kabusys/__init__.py）。
  - Keep a Changelog に基づく初回リリースとして各モジュールをまとめて公開。

- 実行系 / エンジン
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて Paper Trading 用 DB を切り替え（本番 DB と分離）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ監視を実装。
    - デーモンスレッドでセッションを実行し、停止フラグ検知で安全に停止する制御を実装。
    - 起動時にプロセス優先度を設定。

- 監視
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグファイルによりループ終了を実現。
    - DuckDB と SQLite の双方に接続し、監視 DB の初期化処理を呼び出す。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env と .env.local の自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を探索）を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export 構文、クォート、インラインコメント、エスケープシーケンスなどを考慮。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading パス / 監視閾値 / PID/kill フラグパス 等）。
    - 入力値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。未設定必須項目は _require() で例外を送出。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順かつ signal_rank でのタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分へフォールバック（警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮したセクター露出計算と候補除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームでの警告フォールバック。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score 各方式の発注株数決定、単元（lot_size）丸め、per-position 上限・aggregate cap の実装。available_cash 超過時のスケーリングと端数ロットの再配分ロジックを実装。
  - これらをまとめてパッケージエクスポート（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離率）、ボラティリティ（20日 ATR、相対 ATR、出来高関連）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials テーブルから計算。
    - ウィンドウ・欠損データを考慮して None を返す安全設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで動作する設計。
  - research パッケージの public API を整備（src/kabusys/research/__init__.py）。

- AI / ニュース NLP
  - ニュースセンチメントスコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - target_date に対するニュース収集ウィンドウ計算（JST→UTC 変換）。
    - raw_news と news_symbols の集約、記事数・文字数のトリム（1 銘柄あたり最大記事数・最大文字数制限）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出すバッチ実装（バッチサイズ上限、最大同時銘柄数）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ、部分成功時の DB 書き込み戦略（対象コードのみ置換）等のフェイルセーフ設計。
    - API キー未設定時の ValueError。
    - （注）ファイル末尾で記事取得関数の実装が途中で切れているため、実装の続きを要確認。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI で期間指定可能（--from / --to / --db）。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を集計してレポート出力。
    - PASS/FAIL 判定基準（稼働率・成功率・送信率・P95 レイテンシ等）の閾値を定義し、詳細な判定理由を出力。
    - DB 存在チェック・OperationalError による安全なフォールバックを実装。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン止め可能。
    - 能力不足や権限不足時は警告を出して安全にスキップ。

### Changed
- 設計方針の明確化
  - 多くのモジュールで「DB 参照なし — メモリ内計算のみ」「DuckDB / SQLite のみ参照し、外部 API にアクセスしない」などの設計方針を明記。
  - 研究・リサーチコードは pandas 等に依存せず標準ライブラリ＋DuckDB で完結する方針。

- DB 分離
  - Paper Trading（KABUSYS_ENV=paper_trading）時は paper_trading 専用 SQLite を使用して本番 DB と完全に分離する挙動を導入（run_execution.py / Settings.paper_sqlite_path）。

### Fixed
- 環境変数パーサーの堅牢性向上（src/kabusys/config.py）
  - export 付き行、クォートあり/なし、バックスラッシュエスケープ、インラインコメント処理に対応して .env の読み込みをより堅牢に実装。
  - .env の読み込みで読み取り失敗時に警告を出して続行するように修正。

- ポートフォリオ / ポジション決定の端数処理とスケーリング精度向上
  - calc_position_sizes にて aggregate cap 超過時のスケールダウン処理と lot_size 単位での再配分アルゴリズムを実装し、利用可能現金内に安全に収めるよう改善。

### Security
- なし（この差分から推測されるセキュリティ関連の変更はありません。環境変数や API キー取扱いは引き続き注意が必要です）。

### Notes / Known issues / TODO（コード中注記に基づく）
- news_nlp の記事取得処理がファイル末尾で途中で切れているため、完全なパイプライン（記事集約→API送信→結果検証→DB 書き込み）の最終部分は実装・レビューが必要。
- position_sizing: price が欠損（0.0）時にエクスポージャーが過少見積りされる可能性について TODO コメントあり。将来的に前日終値や取得原価をフォールバックすることが検討されている。
- process_priority / set_cpu_affinity は権限不足や未対応 OS ではスキップされる仕様。実運用環境では権限確認が必要。

---

この CHANGELOG は、提供されたコードファイルの関数定義・ドキュメント文字列・ログメッセージ・コメントから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要ならば、個々の機能ごとにより詳細な変更点（関数署名、引数、戻り値、例外挙動など）を追記します。