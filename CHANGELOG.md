CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
注: 以下の履歴は提示されたコードベースの内容から推測して作成したものです（コミット履歴が与えられていないため、実際の変更履歴とは異なる可能性があります）。

Unreleased
----------

- 今後の課題・予定（推測）
  - 単体テスト・統合テストの追加
  - CI/CD（自動デプロイ・品質チェック）の導入
  - ドキュメント（ユーザガイド / 開発者向け設計書）の拡充
  - エラーメトリクス収集・アラート連携（外部サービス）  

0.1.0 - 2026-04-12
------------------

Added
- 初期リリースとして主要コンポーネントを追加
  - 実行系 (Execution)
    - 実取引・ペーパー取引を共に実行可能な起動スクリプト run_execution.py を追加。  
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用する想定。
      - ExecutionEngine の組み立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）。
      - RiskManager にデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec 等）を導入。
  - 監視系 (Monitoring)
    - SystemMonitor をポーリングで動かす run_monitoring.py を追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はログを出してデフォルトを使用）。
      - 監視は環境にかかわらず本番 sqlite_path を参照して初期化。
      - プロセス優先度を起動時に High に設定するフックを追加。
  - 設定管理 (Config)
    - Settings クラスを追加し、環境変数／.env ファイル（.env / .env.local）から設定を解決する自動読み込み機能を提供。  
    - 必須項目の取得ヘルパー（_require）と入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を導入。
    - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、PID/KILL フラグ等のプロパティを用意。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - ユーティリティ
    - process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定関数（set_cpu_affinity）を追加。Windows/Linux/macOS 等に対応し、失敗時は警告でスキップ。
  - ポートフォリオ構築（Portfolio）
    - 銘柄選定・重み付け（select_candidates, calc_equal_weights, calc_score_weights）
    - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
    - ポジションサイズ算出（calc_position_sizes）：risk_based、equal、score 各方式、単元株丸め・aggregate cap スケーリング、コストバッファ対応。
  - 研究モジュール（Research）
    - factor_research: momentum / volatility / value ファクター計算（DuckDB を用いた SQL ベースの実装）。
    - feature_exploration: 将来リターン計算、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク付けユーティリティ等。
  - AI ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI に問い合わせて銘柄ごとのセンチメント ai_score を計算・保存するロジックを追加。  
      - ニュースの時間ウィンドウ計算、記事集約、バッチ（最大 20 銘柄）での API 呼び出し、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）を実装。
  - ツール
    - tools/paper_verification_report.py: ペーパー取引 DB に対する検証レポート生成ツールを追加。  
      - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定（閾値はファイル内定義）を出力。

Changed
- （初期リリースのため該当なし。コード中に多数の既定値・設計方針のコメントを含む）

Fixed / Behaviour improvements
- .env パーサ（config._parse_env_line）を堅牢化
  - export 形式のサポート、クォート内バックスラッシュエスケープ処理、インラインコメントの扱い、クォートなし時の '#' コメント検出ルールなどを実装。
  - ファイル読み込み時に OS 環境変数を保護する protected ロジックを導入（.env.local は override=True）。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合に等金額配分にフォールバックして警告を出すように変更（フォールバックの明示化）。
- apply_sector_cap: unknown セクターはセクター上限チェックの対象外とし、当日売却予定コードをエクスポージャー計算から除外するロジックを導入。
- calc_position_sizes: 単元株（lot_size）丸め、aggregate cap 超過時のスケーリング・端数再配分ロジックを実装。コストバッファの考慮。
- run_monitoring / run_execution: 起動時にプロセス優先度を最初に設定するようにし、DB 接続の初期化（init_monitoring_db）で監視テーブル存在を保証（冪等）。
- process_priority: 未対応 OS の場合は設定をスキップして警告、アクセス権限の問題は警告でフォールバック。

Security
- OpenAI API キーの取り扱いは明示的に引数或いは環境変数（OPENAI_API_KEY）を要求し、未設定時は ValueError を送出して明示的に失敗させる設計を採用。

Notes / Known limitations（コードから推測）
- DuckDB / SQLite のテーブル存在チェックで OperationalError を受けてレポートを N/A 扱いにするフェイルセーフを採用しているが、本番運用ではテーブル整合性チェックの強化が望まれる。
- position_sizing の price 欠損時の扱いについて注釈（TODO）があり、将来的に前日終値や取得原価でのフォールバックが検討対象。
- ai/news_nlp の処理は OpenAI の API レスポンス構造に依存しており、API 側の仕様変更に対する耐性（バリデーション・例外処理）はあるが、部分失敗時のリカバリ戦略は限定的。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）検出に依存するため、配布先での構成に注意が必要。

メタ
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

---

以上。必要であれば、各項目をファイル単位やコミット単位により詳細化（例: 実装箇所の行数や関数名、想定ユースケース、後続作業リスト）できます。どの粒度で出力するか指定してください。