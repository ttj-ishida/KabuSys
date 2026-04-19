CHANGELOG.md
=============

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

[0.1.0] - 2026-04-19
-------------------

Added（追加）
- 基本アーキテクチャと実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory を用いたブローカークライアント生成、スレッド実行と停止フラグ処理を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、監視DB初期化をサポート。

- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数 / .env 自動読み込み、.env パース処理、Settings クラスによる型付き設定アクセス（DBパス、環境種別、Paper Trading 関連設定、閾値等）を実装。PAPER_FILL_MODE の検証や KABUSYS_ENV の検証などを含む。
  - config_setup.py: .env の対話式ウィザードを実装（既存値読み込み、シークレット扱い、ファイル出力）。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パス存在チェック、PyYAML があれば YAML パース検証、live 環境向け警告等を実施。--strict オプション対応。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算）
  - portfolio/portfolio_builder.py: シグナル選定 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights を実装。スコア全ゼロ時のフォールバック挙動を含む。
  - portfolio/risk_adjustment.py: セクター集中抑制 apply_sector_cap、および市場レジームに応じた資金乗数 calc_regime_multiplier を実装。未知レジームでのフォールバック動作を備える。
  - portfolio/position_sizing.py: 発注株数決定ロジック calc_position_sizes を実装。risk_based / equal / score の配分方式、単元株丸め(lot_size)、コストバッファ、aggregate cap スケーリング（残差の分配アルゴリズム）を含む。
  - portfolio/__init__.py: 上記 API をパッケージとして公開。

- ユーティリティを追加
  - utils/logging_setup.py: 統一ログ設定ユーティリティ。コンソール（stdout）と日次ローテーションファイルハンドラをルートロガーに設定。既存ハンドラの二重登録防止、ログディレクトリの解決とフォールバック処理、LOG_LEVEL/LOG_DIR の取り扱い。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティ（psutil 利用）。Windows/Linux/macOS に対応し、権限や未実装時は警告でフォールバック。

- 運用・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。期間フィルタと DB パス指定オプションをサポート。
  - tools/__init__.py: ツールパッケージ初期化。

- 研究用ファクター計算モジュールの追加（実装途中）
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を利用したモメンタム等ファクター計算関数群を追加（モジュール設計・定数・calc_momentum の冒頭実装あり。実装継続予定）。

Changed（変更）
- DB/環境分離ポリシー
  - 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する設計を採用。
  - 監視プロセス（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用する」挙動を明示（監視テーブルを本番監視 DB に集約）。

- 環境変数ロード順と保護
  - config.py にて自動 .env ロードを行う（プロジェクトルート検出成功時）。読み込み順は OS環境変数 > .env.local > .env。OS 環境変数は protected として上書きされないように配慮。

- ログ設定の挙動
  - logging_setup でログディレクトリ作成に失敗した場合、ファイル出力をスキップしてコンソール出力のみで継続する堅牢化。

- 設定ウィザードの利便性向上
  - config_setup で既存 .env の読み込み、シークレット値のマスク表示、選択肢/デフォルト提示、確認プロンプトを実装。

Fixed（修正・堅牢化）
- .env パーサの強化（config.py）
  - export KEY=val 形式への対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメント取り扱い、コメント判定ロジックの改善により .env のパースがより堅牢に。
  - _load_env_file のファイル読み込み失敗時に警告を発するようにして静かに失敗するケースを可視化。

- プロセス優先度設定の安全化（utils/process_priority.py）
  - 未対応 OS や権限不足時に例外で落ちないように警告でフォールバック。Windows/Linux での既存定数へのフォールバック定義を追加。

- ポジション決定ロジックの安定化
  - calc_position_sizes において価格欠損や負値の扱いをログ出力してスキップするようにし、aggregate cap スケーリング時の端数処理と残余配分のアルゴリズムを実装して再現性を確保。

- モニタリングループの堅牢化
  - run_monitoring で check_once() の例外を捕捉してログを出力し、次のポーリングに継続することで監視プロセスの自律復帰性を確保。

Notes（その他）
- デフォルト値や閾値
  - MONITOR_POLL_INTERVAL のデフォルトを 60 秒に設定。0 以下や不正値はデフォルトにフォールバックして警告を出す設計。
  - paper_verification_report の判定閾値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）を初期基準として定義。
  - Settings にて CPU/MEM/DISK 閾値や PID / kill_flag のパス、ログレベル等のデフォルトを提供。

- ドキュメント参照
  - portfolio モジュールや risk/strategy に関する設計は内部ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）を参照している旨の注記あり。将来的に外部ドキュメントへのリンクや追加仕様が想定される。

Known issues / TODO（既知の課題・今後の作業）
- research/factor_research.py は途中で切れている（calc_momentum の実装継続が必要）。
- position_sizing の price 欠損時のフォールバック価格（前日終値や取得原価）を使う改善が TODO として残っている。
- 一部の CLI/ツールは外部依存（PyYAML, psutil, duckdb 等）により挙動が異なるため、インストール手順と依存バージョンの明示が必要。
- ExecutionEngine / SystemMonitor 等の外部コンポーネントの統合テストが不足している可能性があり、E2E テストの整備を推奨。

ライセンス
- このリリースではライセンス情報はソースツリーに依存します。配布時は LICENSE を確認してください。