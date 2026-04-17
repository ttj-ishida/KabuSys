Keep a Changelog 準拠の CHANGELOG.md（日本語）
========================================

全体方針
-------
このリポジトリは日本株自動売買システム KabuSys の初期公開リリースです。  
以下はコードベースから推測して作成した変更履歴（初期リリース / 0.1.0）です。

Unreleased
----------
（今後のリリースで追記）

0.1.0 - 2026-04-17
------------------

Added
- パッケージ基本情報
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
- 実行スクリプト
  - run_execution.py：ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動ループを実装。
    - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid）に対応。
- 監視スクリプト
  - run_monitoring.py：SystemMonitor のポーリングループ起動用スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録する設計。
    - 停止フラグ（data/stop_requested.flag）で安全に終了できる。
- 設定管理
  - config.py：.env 自動ロード機能（プロジェクトルート検出）と Settings クラスを追加。
    - .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env パーサーはコメント行・export 形式・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントの扱いに対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / Paper Trading / 監視閾値 / ログレベル / 環境チェック等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実施。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates：BUY シグナルをスコア順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights：配分重み計算（スコアが全て 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap：セクター集中リスク制御（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数決定、lot_size（単元）丸め、aggregate cap スケーリング、cost_buffer を用いた保守的見積り。
- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value：DuckDB を用いたモメンタム・ボラティリティ・バリュー系ファクターの算出。欠損データへの耐性（データ不足時は None を返却）あり。
  - research.feature_exploration
    - calc_forward_returns：将来リターンの一括取得（複数ホライズン対応、引数検証）。
    - calc_ic：スピアマンのランク相関を用いた IC（Information Coefficient）計算、最小サンプル数チェック。
    - factor_summary / rank：ファクターの統計サマリーおよびランク化ユーティリティ（外部ライブラリに依存しない実装）。
- ニュース NLP（AI）
  - ai.news_nlp
    - raw_news から銘柄別に記事を集約し OpenAI（gpt-4o-mini）経由でセンチメントスコアを計算して ai_scores テーブルへ書き込む設計を追加。
    - バッチ処理、トークン肥大対策（記事数・文字数上限）、429/タイムアウト/5xx 等に対する指数バックオフリトライ、レスポンス検証、スコアクリップ実装。
    - ニュース収集ウィンドウ（JST ベース → UTC 変換）計算ユーティリティを提供。
- ツール
  - tools.paper_verification_report：Paper Trading 検証レポート生成 CLI を追加。
    - 指定期間（--from/--to）や --db オプションで SQLite を指定可能。デフォルトは data/paper_trading.db。
    - 稼働率・注文成功率・送信率・P95 レイテンシなど主要指標を算出し PASS/FAIL 判定を行う。既定の閾値を定義（README 例示）。
- ユーティリティ
  - utils.process_priority：プラットフォーム差を吸収したプロセス優先度設定ユーティリティを追加。
    - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）をサポート。set_cpu_affinity で CPU affinity 固定機能も提供。
    - 権限エラーや未対応 OS では警告ログを出して安全にスキップ。
- DB 初期化 / 監視 DB
  - monitoring.monitoring_db からの init_monitoring_db 呼び出しを各実行スクリプトで保障（監視テーブルの存在を冪等に確保）。
- パッケージエクスポート
  - research / portfolio 等の主要関数を __all__ で公開。

Changed
- （初期リリースのため該当なし。設計上の注意点やフォールバックを随所に実装）

Fixed
- .env パーサー周りの堅牢化
  - export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理などの取り扱いを強化。
- ファクター・リサーチ処理における NULL / データ不足時の安全処理（None を返す、例外を投げない設計）。

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を発生させる仕様（明示的なエラーにより誤動作を防止）。

Notes / Known limitations / Migration
- 依存
  - duckdb, psutil, openai 等の外部ライブラリが必要。実行前にインストールしてください。
- Paper Trading
  - paper_trading モードは本番 DB と分離されますが、paper_trading 用の DB が存在しない場合はファイル作成やデータ投入の手順が別途必要です（tools での検証は事前に DB があることが前提）。
- ニュース NLP
  - AI モジュールは外部 API 利用（課金・レート制限の考慮が必要）、処理時間や失敗時の取り扱い（部分的な書き込みの保護）がコード内で考慮されていますが、運用前に十分なテストを推奨します。
- 単元（lot_size）と手数料スリッページ見積り
  - 現時点では lot_size を共通で扱う設計（将来的な銘柄別単元対応の TODO コメントあり）。
- .env 自動ロード
  - プロジェクトルートの検出は .git または pyproject.toml に依存します。配布後にこれらが存在しない場合は自動ロードをスキップします。
- モニタリング
  - run_monitoring は環境変数 MONITOR_POLL_INTERVAL を整数で受ける。0 以下や不正値はデフォルト 60 秒にフォールバック。

Acknowledgements / Authors
- コードベースから推測して作成した CHANGELOG です。実際のコミット履歴や PR の説明と照合して必要に応じて内容を調整してください。

テンプレート・補足
- 今後のリリースでは各変更をコミット単位で「Added / Changed / Fixed / Deprecated / Removed / Security」に分け、リリースノート（リリース日・セマンティックバージョニング）を明示してください。