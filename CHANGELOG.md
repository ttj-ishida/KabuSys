Keep a Changelog準拠の CHANGELOG.md（日本語）
すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

注意: 以下の履歴は提示されたコードベースの内容から推測して作成したものです。実際のコミット履歴や日付とは異なる可能性があります。

Unreleased
---------
- (なし)

[0.1.0] - 2026-04-19
--------------------
Added
- 実行・監視用のエントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、DB 接続、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、スレッドでのセッション実行・停止フラグ監視、paper_trading 環境時の専用 SQLite (data/paper_trading.db) 利用をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）、停止フラグ検出、例外耐性のある check_once 呼び出し、監視用 DB 初期化を実装。
- 環境設定ユーティリティを実装
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。デフォルト値や説明、シークレット項目のマスク表示を提供。
  - validate_config.py: .env と config/*.yaml の検証 CLI を追加。必須環境変数チェック、パスや YAML の検査、KABUSYS_ENV 別の安全ガード、--strict モードをサポート。
- 設定読み込みと管理
  - config.py: .env 自動ロード機能を追加（プロジェクトルート検出ロジックに基づく）。.env のパースは export 形式、クォート文字、エスケープ、インラインコメントなどに対応。環境変数アクセス用の Settings クラスを提供（各種パス、閾値、paper_trading 用設定など）。
- ログ & プロセス管理ユーティリティを追加
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。既存ハンドラのクリア処理を実装。
  - utils/process_priority.py: プロセス優先度（high/normal/low）設定と CPU affinity 設定をプラットフォーム差分を吸収して実装（Windows / POSIX 対応）。権限不足時は警告を出して安全にフォールバック。
- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定（score 降順 + タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用ロジック（apply_sector_cap）と市場レジームに応じた投資乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバック挙動を定義。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）を実装。単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、コストバッファを考慮したスケールダウンと端数配分を実装。
  - portfolio/__init__.py: 上記 API をエクスポート。
- Paper Trading 向け検証・レポートツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を参照してシステム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力する CLI を追加。閾値による判定基準を定義（稼働率 99% など）。日付フィルタと --db オプションをサポート。

Changed
- ロギングの出力先と初期化の統一
  - 各起動スクリプトから utils.setup_logging を呼び出すことでログ設定を統一。既存ハンドラの重複登録を防止するため、設定時にハンドラをクリアする挙動を導入。
- DB パスの取り扱い
  - Execution エンジンは paper_trading 環境時に専用の paper_sqlite_path を使用し、本番 DB とデータを分離する設計に変更。
  - 監視（monitoring）は環境にかかわらず sqlite_path（本番監視 DB）を使用する旨を明記。

Fixed
- 環境変数パースの堅牢化
  - .env パースでクォートやエスケープ、export プレフィックス、インラインコメントを適切に扱うように修正。不正な行はスキップし、空行・コメントを無視。
- MONITOR_POLL_INTERVAL の入力検証を追加
  - 0 以下や非整数値を設定した場合にデフォルト（60 秒）へフォールバックし、警告を出力するように変更。time.sleep への無効値渡しを防止。

Security
- .env 生成ウィザードにおいて「.env は絶対に Git にコミットしないこと」等の注意喚起をテンプレートに含めた（config_setup.py）。

Deprecated
- (なし)

Removed
- (なし)

Notes / Implementation details
- 設定自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップ。
- process_priority.set_process_priority は権限やプラットフォーム制約により失敗する場合があり、その場合は警告ログを出して処理を継続する設計。
- position_sizing の aggregate cap スケールダウンロジックは lot_size 単位での再配分アルゴリズムを採用し、スケールダウン後の残余キャッシュで端数を再配分する実装を行っている。
- research/factor_research.py はファクタ計算（モメンタム等）の実装を開始しており、DuckDB を使った prices_daily / raw_financials 参照による計算を想定している（ファイル途中での抜粋あり）。

今後の提案（参考）
- DB スキーマ変更やマイグレーション用のスクリプトを追加すると、運用時の互換性管理が容易になります。
- テストカバレッジ（特に position_sizing の資金スケーリング・端数処理や .env パーサ）を充実させると安心です。
- monitoring と execution のユニットテスト／統合テストで stop flag / pid 挙動を検証するテストを追加すると運用上の安全性が高まります。

--- End of CHANGELOG ---