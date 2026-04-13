# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  

最新の変更は上に記載しています。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 全体
  - 初回リリース。パッケージ名: kabusys（__version__ = "0.1.0"）。
  - 基本的な実行/監視/研究/ポートフォリオ/AI ツール群を提供。

- 実行・監視
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用に専用の SQLite DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
    - 実行時にブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを行う。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出す。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを操作（monitoring 用 DB 初期化も実行）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py：環境設定読み込みモジュールを追加。
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順: OS環境変数 > .env.local > .env。OS 環境変数の上書きを防ぐ保護機能あり。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途向け）。
    - .env のパース機能強化:
      - `export KEY=val` 形式に対応
      - シングル/ダブルクォートのエスケープ処理対応
      - インラインコメント認識（クォートあり／なしでの扱いを分離）
    - Settings クラスを提供し、各種環境変数に対するプロパティを追加:
      - J-Quants / kabu API トークン類、LINE トークン
      - duckdb/sqlite のパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE（instant/partial/never/reject の検証）
      - PID / kill-flag パス、kill-flag の起動時クリアフラグ
      - CPU/Memory/Disk の閾値（監視用）
      - KABUSYS_ENV / LOG_LEVEL の検証（有効な値のチェック）
      - 簡易 bool プロパティ（is_live / is_paper / is_dev）

- ツール
  - tools/paper_verification_report.py：
    - Paper Trading DB（デフォルト: data/paper_trading.db）を解析して検証レポートを出力するコマンドラインツールを追加。
    - 指標:
      - 稼働率 (uptime%)
      - 注文成功率（Filled/Created）
      - 送信率（Sent/Created）
      - リスク却下数
      - API レイテンシ（avg / max / P95）
    - 基準値に基づく PASS/FAIL 判定を実装（閾値はソース内定数で調整可能）。
    - 日付範囲フィルタ（--from/--to）と --db オプションをサポート。
    - レポートは N/A 対応および DB 存在チェックを行う。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順の候補選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア 0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中上限チェックと候補フィルタリング）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
  - portfolio.position_sizing:
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" に対応）
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer（手数料・スリッページ考慮）、スケーリングと余剰配分処理を実装
  - portfolio パッケージで上記関数をエクスポート。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) — Windows / POSIX の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) — カレントプロセスを最初の N コアにピン留め（省略可能）。
    - 権限不足等の失敗は警告として扱い、例外を上げないフェイルセーフ設計。

- 研究（Research）
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け、prices_daily/raw_financials を参照して各種ファクターを計算）
    - 各関数はデータ不足時に None を返すなど堅牢に実装。
  - research.feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン）
    - calc_ic（スピアマンランク相関による IC）
    - factor_summary（基本統計量）
    - rank（同順位は平均ランクで処理）
  - research パッケージから zscore_normalize（data.stats 由来）を再エクスポート。

- AI / ニュース NLP
  - ai.news_nlp：
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込み。
    - バッチサイズ、1銘柄あたりの記事・文字数上限、チャンク単位処理（最大 20 銘柄/コール）を実装。
    - 429 / ネットワーク・タイムアウト / 5xx に対して指数バックオフのリトライ（上限あり）を実装。
    - レスポンスの厳格な JSON 検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための限定的 DB 更新ロジックを採用。
    - calc_news_window(target_date) による対象ウィンドウ計算（JST -> UTC 変換）。外部日時に依存しない設計（ルックアヘッド回避）。

### 変更 (Changed)
- 環境・設定
  - .env パーサーの動作を強化し、実運用でありがちな export 形式・クォート・インラインコメントに対応するように変更。OS 環境変数の保護機能を追加。

### 修正 (Fixed)
- 多くの関数で入力検証や None/空データに対する安全なフォールバックを追加（例: P95 計算で空リストに対応、ファクター計算でデータ不足時に None を返す等）。
- sqlite/duckdb 接続のクローズ処理を finally で保証。

### 注意点 (Notes)
- run_monitoring は「監視専用」に設計されており、監視 DB 初期化のために Settings.sqlite_path（本番パス）を使用します。開発や paper_trading 環境で監視データを分離したい場合は環境変数 SQLITE_PATH を適切に設定してください。
- MONITOR_POLL_INTERVAL は整数かつ 1 以上である必要があります。不正な値は 60 秒にフォールバックして警告を出します。
- set_process_priority/set_cpu_affinity はプラットフォーム差分や権限によって失敗する可能性があります。その場合は警告ログを出し処理を継続します（例外は送出しません）。
- ai.news_nlp.score_news は OpenAI API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定の場合は ValueError を送出します。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- duckdb の一部操作（executemany 等）に注意するコメントが残されています。大きなバッチ処理時の互換性を確認してください。

### 既知の制約 / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）である場合、エクスポージャーの過小評価に繋がる箇所がある（コメントで TODO としてフォールバック価格の検討を示唆）。
  - 将来的に銘柄別 lot_size のサポートを検討。
- ai.news_nlp:
  - 実運用ではトークンコストや API レート制限に注意。レスポンス検証・部分更新ロジックは実運用安全性を高めるが、完全冪等ではない操作があるため運用手順を確立することを推奨。
- research モジュールは DuckDB 上の prices_daily / raw_financials の整合性に依存するため、データの欠損により出力が限定される場合がある。

---

今後のリリースでは、テストカバレッジの拡充、エラー監視の強化、銘柄マスタ追加による lot_size/セクター情報の安定化、AI モデル周りの再利用性改善（キャッシュや部分更新の堅牢化）を予定しています。