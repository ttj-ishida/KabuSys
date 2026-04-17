# Changelog

すべての注目すべき変更をこのファイルで管理します。  
このプロジェクトは Keep a Changelog の慣例に従い、セマンティックバージョニングを使用しています。

※ 以下の変更点はリポジトリ内のソースコードから推測して記載しています。

## [0.1.0] - 2026-04-17
### Added
- 基本アプリケーションパッケージを追加
  - パッケージ情報: kabusys (バージョン 0.1.0)
- 実行エントリポイント／サービス
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - プロセス優先度を設定してから実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポートし、デーモンスレッドでエンジンを実行・停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用（環境に依存しない）。
    - 停止フラグ検知による優雅な終了、例外ハンドリング、接続クローズを実装。
- 設定・環境変数管理
  - config.py: .env 自動ロード機能（.env, .env.local）を実装。  
    - .git または pyproject.toml を基準にプロジェクトルートを探索して自動ロード。
    - export KEY=val, コメント、クォートやエスケープに対応した独自パーサを実装。
    - 環境変数の必須チェック（_require）、各種設定プロパティ（DB パス、PID ファイル、監視閾値、PAPER_FILL_MODE など）を提供。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証と便利な is_live/is_paper/is_dev プロパティ。
- 監視関連
  - monitoring_db の初期化呼び出しを各スクリプトで行い、監視テーブルの存在を保証。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定および CPU affinity 設定ユーティリティを追加。  
    - Windows/POSIX の差分を吸収して安全に優先度をセット（アクセス権限エラーは警告でスキップ）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。
    - CLI オプション (--from, --to, --db) と PAPER_TRADING_SQLITE_PATH 環境変数に対応。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアが全て 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中の上限チェック（既存保有比率に基づき候補除外）。unknown セクターは上限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知は警告とフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。  
      - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を考慮した aggregate cap スケーリング。  
      - risk_based モードではリスク許容率（risk_pct）とストップロス（stop_loss_pct）からベース株数を計算。
- リサーチ／ファクター計算
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 偏差を計算。
    - calc_volatility: ATR20、ATR 比率、20 日平均売買代金、出来高変化率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily を結合して計算。
    - 全関数は DuckDB 接続を受け取り SQL で高効率に計算。
  - research/feature_exploration.py:
    - calc_forward_returns: 各ホライズン（デフォルト 1,5,21 日）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・最小レコード数チェックあり）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - research/__init__.py: 主要関数を公開。
- AI ニュース NLP（下書き/実装中）
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント化して ai_scores に書き込むための設計を実装。  
    - バッチ処理（_BATCH_SIZE=20）、トークン肥大対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、±1.0 にスコアをクリップする処理等を含む。  
    - ニュース収集ウィンドウ計算関数 calc_news_window を提供（JST→UTC のウィンドウ変換）。
    - API キー解決やエラー時のフェイルセーフ動作を想定。

### Changed
- データベース関連
  - DuckDB/SQLite を併用する設計を導入（duckdb は分析用、sqlite は監視／発注ログ等の永続化に利用）。
  - run_monitoring は環境に関わらず本番 sqlite_path を参照する方針を明示。
- .env 読み込みの挙動
  - OS 環境変数を保護する protected 機構を導入し、.env.local による上書きをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加（テストでの制御用）。

### Fixed
- 汎用的な堅牢化
  - process_priority/set_cpu_affinity: 権限不足や未実装 API の場合に警告ログを出して安全にスキップするように修正。
  - position_sizing の aggregate スケーリングで端数処理が再現性を持つよう remainder ベースの配分ロジックを実装。
  - paper_verification_report: 各種クエリが存在しないテーブルに対して sqlite3.OperationalError を捕捉して N/A を返すようフォールトトレラント化。
  - .env パーサ: export プレフィックス・クォート文字・エスケープ・インラインコメント等を正しく扱えるように改善。

### Documentation
- 各モジュールに詳細な docstring と設計ノートを追加（PortfolioConstruction.md / StrategyModel.md 等への言及を含む）。  
- tools/paper_verification_report の CLI ヘルプと使用例を追加。

### Security
- OpenAI API キー等の機密情報は環境変数経由で取得する設計（コード中で直接キーを持たない）。

---

今後の予定（コードから推測）
- ai/news_nlp.py の残り部分（記事の抽出 fetch、API 呼び出し、結果保存ロジック）の実装完了。
- ExecutionEngine / Broker クライアントの詳細な統合テスト、paper_trading と live のエンドツーエンド検証。
- 単体テストと CI 設定の追加（.env の安全な取り扱いを含む）。

もしリリース日やセクションの調整、より詳細な変更説明（各関数の挙動差分や設計決定理由）を反映したい場合は、その旨を教えてください。コード差分（git のコミットログ等）を提供いただければ、より正確な CHANGELOG に整形します。