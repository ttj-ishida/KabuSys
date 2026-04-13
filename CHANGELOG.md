CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」フォーマットに準拠しています。  
主にコードベースから推測される新機能・改善点・修正を日本語でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-13
最初の公開リリース。自動売買システム KabuSys のコア機能群を実装／統合しました。

### Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - 環境変数ベースの設定読み込み・管理機能を実装（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み（OS 環境変数を保護する protected モード、読み込み順: OS > .env.local > .env）。
    - 行解析の強化（export 形式、クォート内のエスケープ、インラインコメント処理等）。
    - 必須キー取得用ヘルパー、各種パス・閾値・フラグのプロパティ化。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
- 実行・監視
  - 実行エントリスクリプト: ExecutionEngine 起動スクリプトを提供（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と分離する設計。
    - 起動時にプロセス優先度を設定する仕組みを導入（高優先度に設定）。
    - duckdb を併用して研究データ処理を行うための接続を確立。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository／OrderManager／RiskManager／Reconciler を組み立て、ExecutionEngine を起動するワークフローを実装。
  - 監視エントリスクリプト: SystemMonitor ポーリングループ起動スクリプトを提供（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視用 DB の一貫性を保つため）。
    - check_once の例外を捕捉してログ出力後にループ継続するフェイルセーフを実装。
- ポートフォリオ構築
  - 銘柄選定・重み計算モジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - 候補選定（スコア降順、タイブレークは signal_rank）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - リスク調整モジュールを追加（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター集中制限 apply_sector_cap（当日売却予定銘柄の除外、"unknown" セクターは制限免除）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - 口数（株数）決定モジュールを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング実装。
    - 価格欠損時のスキップ、既存保有との差分のみ発注するロジックを実装。
- 研究（Research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials テーブルから計算する関数を実装。
    - 各関数は欠損データに対して安全に None を返す設計。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Spearman）計算 calc_ic、ランク変換ユーティリティ rank、統計サマリー factor_summary。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。
- AI ニュース NLP
  - ニュースセンチメントスコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI API（デフォルト model: gpt-4o-mini）でバッチスコアリング。
    - スコアは ±1.0 にクリップし、結果は ai_scores テーブルへ部分置換（DELETE→INSERT）で書き込み。
    - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30 → UTC に変換）を実装。
    - API 呼び出しはバッチ（最大 20 銘柄）で行い、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーションとフェイルセーフ（失敗しても他の銘柄処理を継続）。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収する set_process_priority。
    - CPU 数を指定して最初の N コアにピン止めする set_cpu_affinity。
    - 権限不足や未対応環境では警告を出して安全にスキップ。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI で期間指定（--from / --to）と DB パス指定（--db）を受け付け、paper_trading DB を解析してレポート出力。
    - 主な指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - PASS/FAIL 基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms など）。
    - P95 の計算、DB 存在チェック、テーブル未存在時の耐性を実装。

### Changed
- データベース取扱い
  - 監視処理（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する方針に統一（監視データの一貫性確保）。
  - 実行処理（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離。
- 設定読み込み
  - .env 行パースの堅牢化（クォート内のエスケープ処理、コメント判定の改善、export 形式対応）。
  - .env.local を .env より優先して上書き（override=True）する挙動を採用。
- ロギング／起動処理
  - run_* スクリプトの起動時にプロセス優先度を最初に設定するように変更（set_process_priority("high") を呼び出す）。
  - check_once の例外を catch して監視ループを継続する堅牢化。

### Fixed
- 環境変数値検証と安全なフォールバックを実装
  - MONITOR_POLL_INTERVAL が 0 以下や不正な値の場合、警告を出してデフォルト（60 秒）にフォールバックするように修正（run_monitoring）。
  - PAPER_FILL_MODE のバリデーションを追加（許容値チェック、無効値で ValueError）。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックを追加して早期エラー検出。
- DB / SQL の堅牢化
  - paper_verification_report: テーブル未存在やデータ欠落に対して sqlite3.OperationalError を捕捉してレポート生成を継続する耐性を追加。
  - DuckDB クエリ側でウィンドウやカウント条件によりデータ不足時に None を返すよう安全に設計（factor_research, feature_exploration）。
- process_priority の権限不足ハンドリング強化（AccessDenied 等を警告してスキップ）。

### Security
- OpenAI API キーの扱い
  - news_nlp.score_news では api_key を引数で渡すことが可能で、渡さない場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させることで誤った無鍵実行を防止。

### Documentation
- 各モジュールに詳細な docstring と使用例を追加。特に以下の点を明確化：
  - 設定項目（Settings プロパティ）と環境変数名・デフォルト値。
  - run_execution / run_monitoring の起動挙動と DB パスの扱い。
  - portfolio モジュールのアルゴリズム設計思想（PortfolioConstruction.md 参照）や将来の拡張点（銘柄別 lot_size）。
  - news_nlp の API 呼び出しフロー、タイムウィンドウ定義、出力 JSON 仕様。

### Removed
- 該当なし（初期リリースのため削除は実施していません）。

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要に応じて各項目を修正・補完してください。