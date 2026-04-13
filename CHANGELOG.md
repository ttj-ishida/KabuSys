# Changelog

すべての重要な変更を本ファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

## [Unreleased]
- （保留）次回リリース向けの変更点はここに記載します。

---

## [0.1.0] - 2026-04-13
初期リリース — コア機能一式を実装しました。

### 追加
- アプリケーション基盤
  - パッケージ情報を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数／.env 管理機能を実装。
    - 自動 .env ロード（プロジェクトルート判定: .git / pyproject.toml を探索）。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 必須環境変数未設定時に明確な例外を投げる _require() を提供。
    - 多数の設定プロパティを実装（J-Quants / kabuAPI / LINE / DB パス / PID ファイル / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）を追加。

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動エントリを実装。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、Engine を起動。
    - DuckDB / SQLite の接続確保と確実なクローズ処理。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) - Windows / POSIX（Linux/Mac/FreeBSD）に対応し、権限不足等はログでスキップ。
    - set_cpu_affinity(cpu_count) - 指定コアへのピン留め（利用不可・権限不足では警告スキップ）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順で上位 N 選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコアが 0 の場合は等配分へフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限。売却予定銘柄を除外できる）
    - calc_regime_multiplier（市場レジームに応じた乗数。未知レジームはフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes（risk_based / equal / score の割付方式に対応）
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）、cost_buffer による保守的見積り
    - 価格欠損時のスキップやログ出力等の堅牢性を考慮

- リサーチ・ファクター計算
  - research/factor_research.py
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER、ROE。raw_financials と prices_daily を結合）
    - DuckDB を用いた効率的なウィンドウ集計を採用
  - research/feature_exploration.py
    - calc_forward_returns（複数ホライズンの将来リターンを同時取得）
    - calc_ic（スピアマンランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランク）
  - research パッケージは kabusys.data.stats の zscore_normalize を再エクスポート

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントをスコア化、ai_scores へ書き込み。
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウ選定（UTC 変換済み）。
    - バッチ処理（最大 20 銘柄／回）、トークン過大対策（記事数・文字数のトリム）、429/5xx 等のリトライ（指数バックオフ）を実装。
    - API キー未設定時は明示的なエラーを発生。
    - レスポンス検証、スコアのクリップ（±1.0）、部分失敗時の既存スコア保護（対象コード絞り込みで DELETE→INSERT）等のフェイルセーフ設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading SQLite（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力する CLI を追加。
    - 判定基準（稼働率・成功率・送信率・P95 レイテンシ）を定義し PASS/FAIL を返す。
    - SQL の存在チェックやテーブル未存在時の扱いを考慮（sqlite3.OperationalError を捕捉して N/A を扱う）。

### 変更
- なし（初期リリースのため既存動作からの変更点はありません）。

### 修正（バグ修正 / 安全性向上）
- 各所で堅牢性を強化
  - MONITOR_POLL_INTERVAL の不正値に対しデフォルトへフォールバックして ValueError を回避（run_monitoring）。
  - init_monitoring_db 呼び出しを冪等に：monitoring テーブルが存在することを保証（両エントリポイントで実行）。
  - SQLite / DuckDB 接続は finally で必ずクローズ。
  - .env 読み込み失敗時は警告を出して処理を継続（テストや CI での扱いを容易に）。
  - process_priority・CPU affinity は権限不足や未サポート OS を検出して警告ログを出し、安全にスキップ。

### 削除
- なし

### 注意 / 既知の制限
- position_sizing 等で price が欠損（0.0）の場合、エクスポージャー算出が過小見積になり得る旨の TODO コメントあり。将来的にフォールバック価格（前日終値など）を導入予定。
- ai/news_nlp の処理は OpenAI API に依存するため、API 利用料とレート制限を考慮する必要があります。
- calc_forward_returns の horizons は 1〜252 日に制限しているため、それを超える指定はエラーになります。
- run_monitoring は監視 DB に本番 sqlite_path を利用する設計になっているため、環境に応じた運用注意（paper_trading 環境でも本番監視を行う仕様）。

---

今後の予定（例）
- 単体テスト・統合テストの拡充（特に AI 周り・DB マイグレーション）。
- position_sizing の銘柄別 lot_size 対応、価格フォールバックの導入。
- ai/news_nlp のエラー回復性改善とロギング強化。