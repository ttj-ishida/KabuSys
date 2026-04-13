CHANGELOG
=========

すべての注目すべき変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
-------------

- なし

0.1.0 - 2026-04-13
------------------

Added
- 初回公開リリース。
- 基本アーキテクチャと主要コンポーネントを実装。
  - 実行・監視のエントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時に MockBrokerClient を利用し、paper_trading 用の SQLite（data/paper_trading.db または環境変数で指定）に完全分離して記録する挙動を実装。
      - 起動時にプロセス優先度を設定（高優先度）。
      - duckdb と sqlite の接続初期化、監視テーブルの冪等な初期化を実施。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログを出力してデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨を明示。
      - 起動時にプロセス優先度を設定（高優先度）。
  - 設定管理
    - config.Settings クラスを実装。環境変数（および .env/.env.local 自動読み込み）から各種設定を取得。
    - .env 自動ロード:
      - プロジェクトルート（.git または pyproject.toml を起点）を探索して .env/.env.local を読み込み。OS 環境変数は保護され、.env.local は上書き可能。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パーサーは export 構文、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 各種バリデーションを実装:
      - KABUSYS_ENV（development / paper_trading / live のみ有効）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ）
      - PAPER_FILL_MODE（instant/partial/never/reject のみ）
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコア合計 0 の場合は等金額にフォールバック）。
    - portfolio.risk_adjustment: セクター集中制限の適用（既存保有のセクターエクスポージャ計算、上限超過セクターの新規候補除外）、市場レジームに応じた投下資金乗数の計算（bull/neutral/bear のマッピング、未知レジームは警告のうえフォールバック 1.0）。
    - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を考慮した保守的見積り、lot 単位での再配分ロジックを実装。
  - 研究モジュール（DuckDB 利用）
    - research.factor_research:
      - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials テーブルから計算。
      - データ不足時は None を返す設計。
    - research.feature_exploration:
      - 将来リターン calc_forward_returns（複数ホライズン対応、ホライズン引数検証あり）。
      - ランク相関 IC（Spearman） calc_ic、ランク生成ユーティリティ rank、ファクター統計サマリ factor_summary を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research.__init__: zscore_normalize（kabusys.data.stats）等をエクスポート。
  - AI ニュース NLP
    - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ書き込み。  
      - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx 等での指数バックオフリトライ、レスポンスの厳密な検証、スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護する更新戦略（対象コードで絞って DELETE → INSERT）を実装。
      - calc_news_window による JST ベースの時間窓計算を提供。日時の扱いでルックアヘッドバイアスを防ぐため datetime.today()/date.today() を直接参照しない設計。
  - ツール
    - tools.paper_verification_report:
      - Paper Trading 用 DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI スクリプトを追加。
      - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計し、閾値による PASS/FAIL 判定を出力（閾値はソース内定義）。期間フィルタ（--from/--to）や --db オプションに対応。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度設定と CPU affinity 設定を提供。権限不足等の失敗は警告ログでスキップするフェイルセーフを実装。

Changed
- n/a（初回リリースのため既存変更はなし）

Fixed
- n/a（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する仕様。未設定時は ValueError を送出して明示的に扱うようにしている（安全側での失敗）。

Notes / Implementation details
- 監視ループ（run_monitoring）は MONITOR_POLL_INTERVAL の不正値に対して警告しデフォルト 60 秒にフォールバックするため、安全に運用可能。
- Settings は環境変数の検証を行い、不正な値（例: KABUSYS_ENV の未知値や PAPER_FILL_MODE の不正値）で起動時に早期にエラーを出す設計になっている。
- .env 読み込みはプロジェクトルート探索に依存するため、パッケージ配布後でもカレントワーキングディレクトリに依存しない堅牢な実装。
- DuckDB / SQLite を併用する設計。研究系機能は DuckDB（分析向け）を使用し、ランタイム監視や注文ログ等は SQLite を使用する想定。

今後の改善案（Roadmap）
- position_sizing の lot_size を銘柄別に持たせる（stocks マスタの導入）。
- apply_sector_cap の price 欠損時のフォールバックロジック（前日終値や取得原価）を追加。
- news_nlp のレスポンス検証やリトライのさらに堅牢化（部分失敗の詳格納、メトリクス出力）。
- テストカバレッジの拡充（単体テスト・統合テスト）、CI ワークフローの追加。

---