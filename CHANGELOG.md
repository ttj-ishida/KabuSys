Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠してバージョニングしています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-24
-----------------

Added
- 初回リリースを公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - プロセス優先度を高く設定して起動。PID 管理・停止フラグに対応。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。  
    - BrokerClientFactory によるブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
- 監視スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してフォールバック）。  
    - 監視は環境にかかわらず本番用 sqlite_path を使用。停止フラグファイル検出で安全に終了。
- 設定管理・ウィザード・検証
  - config.py: Settings クラスを導入。.env の自動読み込み機能（.env → .env.local の順、OS 環境変数を保護）と堅牢な .env パーサ（export 形式、引用符付き値、エスケープ、コメント処理対応）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。各種設定プロパティ（DB パス、ログレベル、Paper Trading 用設定、監視閾値 など）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（テンプレート出力、シークレットマスク、確認プロンプト）。.env の書式と推奨項目を明示。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数や DB パス、config/*.yaml の存在・パース検証、KABUSYS_ENV の妥当性チェック、production 向けの安全ガードを実装。--strict モードあり（警告を FAIL 扱い）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル候補選定と等分配/スコア加重配分関数を追加（重みゼロ時のフォールバックロジック含む）。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と市場レジームに基づく資金乗数 calc_regime_multiplier を追加（レジーム不明時のフォールバックとログ警告を含む）。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score の配分方式、個別上限・aggregate cap、lot_size 単位丸め、コストバッファ対応、スケーリングロジック）を追加。
  - portfolio/__init__.py: 上記関数群を公開。
- 解析・リサーチ
  - research/factor_research.py: DuckDB 接続を使ったファクター計算モジュール骨子（モメンタム・移動平均・ATR・流動性等の設計および関数群の実装方針）を追加（prices_daily / raw_financials に依存）。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout への StreamHandler（標準出力）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。  
    - LOG_DIR/LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows / POSIX に対応、アクセス権限エラーは警告で無視）。CPU affinity 設定関数も提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（P95 など）を集計し PASS/FAIL 判定を行う。日付フィルタや DB パス指定をサポート。
- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- 機密情報（API トークンやパスワード）を .env ウィザードでマスク表示する運用支援を追加。設定検証で本番環境（KABUSYS_ENV=live）向けの注意喚起を行う。

Notes / Implementation details
- run_monitoring と run_execution は停止フラグ（data/stop_requested.flag）・PID ファイルを用いた外部制御に対応。監視ループは例外を捕捉してログ記録しつつ継続する設計。
- position_sizing の aggregate cap は lot_size（単元）単位で丸めた上で、残余キャッシュを最大限活用するため残差に基づく再配分ロジックを実装。
- .env パーサはクォート内のエスケープを正しく処理し、コメントの扱いも改善（非クォート時の # の取り扱いは直前が空白/tab の場合のみコメントとして認識）。
- DuckDB と SQLite を併用するアーキテクチャを採用（分析は DuckDB、運用ログ / 監視は SQLite）。

Deprecated
- なし

Removed
- なし

Acknowledgements
- 本リリースはローカル実行・ペーパートレード・本番運用を想定した基本的な CLI とライブラリ群の初期実装を提供します。今後、テストカバレッジの追加、ファイル I/O のエラーハンドリング強化、銘柄別単元対応などを予定しています。