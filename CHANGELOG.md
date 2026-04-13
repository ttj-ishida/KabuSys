# Changelog

すべての notable な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

### Added
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-13

初回リリース。KabuSys のコア機能を実装・公開しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージエクスポートを整理（portfolio、strategy、execution、monitoring を __all__ に含める）。

- 設定・環境読み込み
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から以下の設定を取得：
    - J-Quants / Kabu API / LINE / DB パス / 監視関連閾値 / 実行環境（development/paper_trading/live）など。
  - .env 自動ロード実装：
    - プロジェクトルート（.git または pyproject.toml を探索）を検出して .env / .env.local を自動読み込み。
    - 読み込み順は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーはクォート文字・エスケープ・export プレフィックス・インラインコメントを考慮して堅牢に処理。
  - .env の上書き制御（override と protected）を実装し、OS 環境変数の保護を可能に。

- 実行ユーティリティ
  - プロセス優先度設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level: "high" | "normal" | "low")：Windows / POSIX を吸収して優先度を設定。
    - set_cpu_affinity(cpu_count: Optional[int])：カレントプロセスの CPU affinity を設定（権限や未対応環境では警告を出してスキップ）。
    - 権限不足や未対応プラットフォームに対しては安全にフォールバックする実装。
  - 実行エントリスクリプト：
    - run_execution.py：ExecutionEngine 起動スクリプト。プロセス優先度を High に設定し、paper_trading 環境では専用の paper_trading DB を使用。Broker クライアントのファクトリ、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て ExecutionEngine を実行。
    - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する設計。プロセス優先度設定と DB 初期化を行う。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py
    - select_candidates：BUY シグナルをスコア降順（同点は signal_rank）で上位 N を選択。
    - calc_equal_weights、calc_score_weights：等金額配分・スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし WARNING）。
  - risk_adjustment.py
    - apply_sector_cap：既存保有のセクター別エクスポージャを計算し、指定上限を超えるセクターの新規候補を除外（"unknown" セクターは上限適用対象外）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes：weights と候補リスト・ポートフォリオ情報から各銘柄の発注株数を算出。
      - allocation_method に "risk_based" と "equal"/"score" をサポート。
      - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）を考慮してスケールダウンするアルゴリズムを実装。
      - cost_buffer を導入し、手数料・スリッページを保守的に見積もる。
      - 価格欠損（<=0）に対してはスキップし、ログ出力で通知。

- 研究（research）
  - factor_research.py（DuckDB ベースのファクター計算）
    - calc_momentum：1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。データ不足時は None を返す。
    - calc_volatility：20日 ATR、ATR/価格比、20日平均売買代金、出来高比率を計算。true_range 計算で NULL 伝播を正しく扱う。
    - calc_value：raw_financials から最新の財務データを取得し PER/ROE を計算。target_date 以前の最新レコードを銘柄ごとに取得する。
  - feature_exploration.py（特徴量・統計ユーティリティ）
    - calc_forward_returns：将来リターン（複数ホライズン）を計算。ホライズンは検証制約（1〜252 営業日）。
    - calc_ic：Spearman（ランク）による IC を計算（同順位は平均ランク処理）。有効レコードが 3 未満なら None。
    - rank、factor_summary：ランク付け・基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの公開 API を整理（zscore_normalize を含む）。

- AI ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコアを算出し ai_scores テーブルへ書き込み。
    - 前日 15:00 JST ～ 当日 08:30 JST のタイムウィンドウを UTC に変換して対象記事を選択する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/コール）、文字数・記事数制限（記事数: 最大 10、文字数: 最大 3000/銘柄）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（最大 3 回）。
    - レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分失敗時も既存スコアを保護する DELETE/INSERT ロジックを採用。
    - OPENAI_API_KEY が未指定の場合は例外を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - レポートには稼働率（uptime）、注文成功率、送信率、P95 レイテンシ、リスク却下数などを出力。閾値を定義し PASS/FAIL の判定を行う。
    - 日付フィルタ (--from / --to) をサポート。DB 未存在時はエラーメッセージを出力して終了。
    - P95 の計算、NULL データへの耐性（OperationalError のフォールバック処理）を実装。

### Changed
- ログ出力とフォールバック動作を多くの箇所で導入：
  - MONITOR_POLL_INTERVAL のパース時、0 以下や不正値はデフォルト（60 秒）へフォールバックし警告ログを出力（run_monitoring.py）。
  - process_priority の優先度設定・CPU affinity 設定で、権限エラーや未対応環境時に警告を出して処理を続行するように変更。
  - .env の上書き処理に protected set を導入し、OS 環境変数を保護。

### Fixed
- データ不足/NULL に対する扱いを強化：
  - factor_research / volatility の true_range 計算で high/low/prev_close の NULL を適切に伝播させ、cnt による閾値判定を厳密化。
  - calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックしてログ出力。
  - calc_position_sizes: price が欠損または 0 の場合をスキップし、誤発注を防ぐガードを追加。

### Security
- API キーの取り扱いに関する注意を追加：
  - OpenAI キーは引数または環境変数 OPENAI_API_KEY から読み込み、未設定時は ValueError を送出して早期に失敗させる設計。

### Notes / Other
- DB 初期化（監視テーブル）を idempotent に行う init_monitoring_db を実行することで、実行環境に依存せず監視用テーブルの存在を保証。
- run_execution は paper_trading 環境で paper_trading の専用 SQLite を使用することで、本番 DB との完全分離を実現。
- ドキュメント参照：各モジュール内に PortfolioConstruction.md / StrategyModel.md 等に基づく実装コメントを多数含む（実装方針と注意点の明記）。

---

### Breaking Changes
- なし（初回リリース）。

---

（注）本 CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やコミットメッセージが存在する場合は、そちらに合わせて更新してください。