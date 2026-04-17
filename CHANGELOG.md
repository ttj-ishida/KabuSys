# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは、提供されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased: 今後の開発用（現状なし）
- 各バージョン: リリース日と主要変更点（Added / Changed / Fixed / Deprecated / Removed / Security）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初回リリース。プロジェクトの基本機能（監視、実行エンジン、設定管理、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ツール）が実装されています。

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開 API を __all__ に定義）。

- 設定管理
  - kabusys.config.Settings：.env/.env.local の自動読み込み（プロジェクトルート検出）と環境変数取得ラッパーを提供。
  - .env パーサは export 形式、クォートやインラインコメント、エスケープに対応。
  - 各種設定プロパティ（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading 設定 / 監視閾値 / ログ・環境判定など）を実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 監視（Monitoring）
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB に接続。
    - duckdb 接続も確立。
    - 起動時にプロセス優先度を high に設定（utils.process_priority を利用）。

- 実行エンジン（Execution）
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して発注・約定を完全分離。
    - BrokerClientFactory を通じてブローカークライアントインスタンスを生成（Mock を含む実装を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - PID ファイル、停止フラグ（data/stop_requested.flag）による起動制御・安全停止。
    - リスク管理のデフォルトパラメータを設定し、初期ポートフォリオ値を broker.get_available_cash() で取得。

- ポートフォリオ構築（Portfolio）
  - portfolio.portfolio_builder
    - select_candidates：BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights：等金額配分。
    - calc_score_weights：スコア正規化配分（全スコアが0の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap：セクター集中上限（max_sector_pct）の判定・候補除外（"unknown" セクターは無視）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に基づく投下資金乗数（フォールバックロジックを含む）。
  - portfolio.position_sizing
    - calc_position_sizes：weight/candidates/portfolio_value 等から発注株数を計算（allocation_method: risk_based, equal, score）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的コスト見積り、残差処理のフェアな配分ロジックを実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority：Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。権限不足時は警告してスキップ。
    - set_cpu_affinity：カレントプロセスの CPU affinity を最初の N コアに固定する機能（権限不足時は警告してスキップ）。
    - psutil を利用した堅牢な実装。

- リサーチ（Research）
  - research.factor_research
    - calc_momentum：1/3/6 ヶ月リターン、200 日移動平均乖離率（MA200）を DuckDB 上で計算。
    - calc_volatility：20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算（NULL ハンドリング含む）。
    - calc_value：raw_financials と当日の株価から PER、ROE を計算（過去最新の財務レコードを取得）。
  - research.feature_exploration
    - calc_forward_returns：複数ホライズン（デフォルト 1/5/21 営業日）の将来リターンを一括取得。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード不足時は None）。
    - factor_summary：count/mean/std/min/max/median を計算（None 値除外）。
    - rank：同順位は平均ランクを割り当てるランキングユーティリティ。
  - research パッケージは zscore_normalize（kabusys.data.stats 経由）を公開 API に含む想定。

- AI ニュース NLP（ニュースセンチメント）
  - ai.news_nlp
    - raw_news / news_symbols を銘柄毎に集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込み。
    - バッチ処理（銘柄単位で最大 _BATCH_SIZE=20）、1銘柄当たりの文字数/記事数制限、429/ネットワーク/5xx のリトライ／指数バックオフ、レスポンスバリデーション、スコアクリッピングなどフェイルセーフな設計。
    - calc_news_window：target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を提供。
    - score_news：API キー解決、タイムウィンドウ計算、記事集約、API 呼び出しおよび DB 書き換えを行う関数を実装（環境変数 OPENAI_API_KEY をサポート）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成ツール（CLI）。
    - 検証指標・閾値を定義（稼働率、注文成功率、送信率、P95 レイテンシ等）。
    - SQLite（paper_trading DB）から system_status / trade_logs / risk_logs を集計し、PASS/FAIL 判定および各種統計（平均/最大/P95/割合）を出力。
    - --from/--to/--db オプションをサポート。DB が存在しない場合はエラーメッセージを表示。

- DB 接続
  - sqlite3（監視用 / paper trading 別DB）と DuckDB を併用する設計を採用。監視テーブル初期化用の init_monitoring_db を使用。

### Changed
- 初回公開のため履歴変更なし。

### Fixed
- 初回公開のため既知のバグ修正履歴なし。
  - 注意: ai/news_nlp のソーススニペットは切れた状態で提供されているため、実装ファイル全体が存在することを前提に記載しています。実運用前に該当ファイルの完全性を確認してください。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーや各種シークレットは Settings 経由で環境変数から取得する設計。ローカル .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。

## 警告・注意点（実装から推測）
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」と明記されているため、開発環境で実行すると本番 DB にアクセスしてしまう危険があります。意図的な設計だが運用時は注意が必要。
- position_sizing の price 欠損時の注記（TODO）や apply_sector_cap の price が 0 の場合の過小評価リスクなど、データ欠損に対するフォールバック処理の拡張余地あり。
- utils.process_priority / set_cpu_affinity は権限不足や未サポート OS で失敗する可能性があるが、警告ログで安全にスキップする実装。
- ai/news_nlp は API 呼び出しに対する堅牢なリトライ設計があるが、OpenAI の利用制限やコスト管理は運用側で配慮が必要。
- DuckDB の executemany に関する注意（空パラメータの排除） をコメントで考慮している。

---

（この CHANGELOG は提供されたコード内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。実運用向けには Git の履歴に基づく正確な CHANGELOG を併せて作成してください。）