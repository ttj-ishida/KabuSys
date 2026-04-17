CHANGELOG
=========

すべての重要な変更はこのファイルに記録されます。  
形式は「Keep a Changelog」準拠です。

[Unreleased]
-------------

- （現在のコードベースは初回リリース相当の機能群を含みます。次バージョンでの追加・修正点はここに追記してください。）

0.1.0 - 2026-04-17
------------------

Added
- 初期リリース: KabuSys コア機能群を追加。
  - 実行・監視
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。  
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。  
      - エンジンはデーモンスレッドで run_session を実行し、data/stop_requested.flag による停止検知・PID ファイル（data/execution.pid）管理に対応。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。  
      - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。  
      - プロセス優先度を High に設定するフックを呼び出し、停止フラグでループ停止。
  - 設定管理
    - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出 .git / pyproject.toml）。  
      - export KEY=val 形式やクォート文字列、バックスラッシュエスケープ、インラインコメントの扱いに対応したパーサ実装。  
      - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。  
      - Settings クラスで環境変数の必須チェック・型変換・値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を提供。
  - データベース統合
    - DuckDB 接続サポート（duckdb 経由）および SQLite 初期化ユーティリティ（init_monitoring_db）を利用。
  - ポートフォリオ構築（純粋関数）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights。全スコアが 0 の場合は等分配にフォールバック）。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく乗数計算（calc_regime_multiplier。未知レジームは警告して 1.0 にフォールバック）。
    - portfolio.position_sizing: position size 計算（risk_based / equal / score）。  
      - 単元株（lot_size）丸め、max_position_pct / max_utilization、cost_buffer を用いた保守的コスト見積り、aggregate cap によるスケーリング、残差分の lot 単位での追加配分ロジックを実装。
  - 研究機能（DuckDB ベース）
    - research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、出来高系）、バリュー（PER、ROE）計算。SQL ベースでの実装。
    - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - AI ニュース NLP
    - ai.news_nlp: raw_news から銘柄別センチメントを算出して ai_scores に書き込む機能を実装。  
      - OpenAI（gpt-4o-mini）を用いた JSON モードでのバッチスコアリング（最大バッチ 20 銘柄）。  
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ、レスポンスバリデーション、±1.0 でのクリップ、部分失敗に耐える DB 更新（対象コード絞り込みで DELETE→INSERT）などフェイルセーフ設計。  
      - ニュース時間ウィンドウ計算ユーティリティ（calc_news_window）を提供。
  - CLI ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成ツールを追加。  
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して判定（PASS/FAIL）を表示。  
      - P95 計算、期間フィルタ、DB 存在チェック、N/A 表示などに対応。
  - ユーティリティ
    - utils.process_priority: set_process_priority（Windows / POSIX の差分吸収）と set_cpu_affinity（最初の N コアに固定）を実装。権限不足や未対応 OS でも安全にフォールバックして警告を出す。

Changed
- 設計上の堅牢化とフェイルセーフ化を多数導入。
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉しログ出力後に次ポーリングへ継続するように変更（監視の高可用性）。
  - run_execution で監視テーブルの存在を保証するために init_monitoring_db を冪等に呼び出すようにした。
  - .env 読み込みの挙動を明確化（読み込み順序: OS 環境 > .env.local > .env、OS の既存変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による抑止を追加。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証ロジックを追加し、不正値で明確なエラー（ValueError）を発生させるようにした。

Fixed
- 入力や欠損データに対する耐性向上。
  - research / factor 計算でデータ不足時に None を返すことで downstream がクラッシュしないように設計。
  - tools.paper_verification_report はテーブル不存在やクエリエラー時に安全に N/A を表示するように例外を扱う。
  - portfolio.position_sizing は価格欠損（None/0）を検出してスキップし、過剰発注を避けるチェックを実装。
  - utils.process_priority / set_cpu_affinity は AccessDenied 等の例外をログ警告に変換して処理を継続するようにした。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を送出し明示的にエラーにすることで誤った公開を防止。
- .env 自動読み込みはデフォルトで有効だが、明示的なフラグで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Migration
- 監視用 DB: run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Paper Trading の検証データは paper_sqlite_path（data/paper_trading.db）に分離してください。
- MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）を与えた場合はデフォルト（60 秒）にフォールバックして警告します。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject" のみです。不正値は起動時に例外を発生させます。
- calc_position_sizes の lot_size は現状全銘柄共通の想定。将来的な銘柄別単元対応のため拡張ポイントあり（TODO コメントあり）。

開発者向け
- パッケージバージョンは __version__ = "0.1.0" に設定済み。
- モジュールの公開 API は各パッケージの __init__.py で整理済み（portfolio / research 等）。

今後の予定（例）
- ニュース NLP の部分失敗時におけるより細かなロールバック戦略の追加。
- 銘柄別 lot_size マスタ導入による position sizing の拡張。
- DuckDB の書き込みパス最適化（bulk upsert 等）の検討。