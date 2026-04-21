CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付は本コードベースの現状（ファイル内容）から推定しています。

Unreleased
----------

（現時点で未リリースの差分はありません）

[0.1.0] - 2026-04-21
-------------------

初回リリース。日本株自動売買システム "KabuSys" の基本機能群を実装したリリースです。
主な追加・変更点は以下のとおりです。

Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルート/data/stop_requested.flag を検知して行う。監視用 DB は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db または環境変数で指定）を使用し、本番 DB と分離する。プロセス優先度上げ、PID ファイル管理、停止フラグ検出によるシャットダウン制御を実装。

- 設定管理
  - config.py: 環境変数/ .env 自動読込機能を搭載。プロジェクトルート検出（.git または pyproject.toml）を行い、.env と .env.local の順序で読み込む（OS 環境変数は保護）。クォートやエスケープ、inline コメント等に対応した .env パーサを実装。Settings クラスに各種プロパティ（DB パス、KABUSYS_ENV 検証、PAPER_FILL_MODE バリデーション、監視閾値など）を追加。

- 設定支援ツール
  - config_setup.py: .env の対話式ウィザードを実装。初期 .env 作成や既存 .env の更新を支援（シークレットのマスキング、デフォルト値、説明テキストを表示）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番時のガード条件チェック（LINE 通知設定や Kill Switch 設定）を実施。--strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選別（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 発注株数計算ロジック（calc_position_sizes）を実装。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した算出を行う。

- ユーティリティ
  - utils.logging_setup: ルートロガーに対する統一的なログ設定ユーティリティを追加。コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）かつ 30 日保持。LOG_DIR / LOG_LEVEL によるカスタマイズ、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils.process_priority: Windows/Linux の差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足等の例外時は警告を出してスキップする安全設計。

- ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite から稼働性・注文成功率・送信率・レイテンシ（P95）・リスク却下数を集計し、PASS/FAIL 判定を行う検証レポートジェネレータを実装。閾値（稼働率 99%、成立率 90% 等）を定義。

- リサーチ基盤（部分実装）
  - research.factor_research: DuckDB 接続を受け取りファクター（Momentum / Value / Volatility / Liquidity）を計算するモジュールを追加（モメンタム関数等、設計と一部実装を含む）。DuckDB を用いた価格・財務データ参照を想定。

Changed
- .env 読み込みの挙動を明確化
  - 自動読込はデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。読み込み順は OS env > .env.local > .env（.env.local は .env を上書き、ただし OS 環境変数は保護）。これにより環境に依存せず安全に設定を上書きできる。

- ログ出力の統一
  - 起動スクリプトから必ず setup_logging を呼ぶ設計になっており、標準出力とファイルの両面で一貫したログが得られるよう変更。

Fixed
- run_monitoring: MONITOR_POLL_INTERVAL が不正（非数や 0 以下）の場合にデフォルト値を使用してエラーを回避するようにした（time.sleep に渡す値の検証を追加）。
- process_priority / logging_setup: 権限不足やファイル作成失敗時に例外で落ちずに警告ログを出し処理を継続する堅牢化を実施。

Security
- .env 生成時の注意書きを config_setup に追加（.env を Git にコミットしない旨の明記）。
- シークレット値はウィザード中にマスク表示するなど、取り扱い上の配慮を追加。

Deprecated
- なし

Removed
- なし

Breaking Changes
- Settings におけるバリデーション強化
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL、PAPER_FILL_MODE の値チェックが厳密になり、無効な値の場合は ValueError を送出するようになった。既存環境の値が正規値でない場合は起動前に修正が必要。

Notes / Implementation details
- ExecutionEngine は paper_trading 時に broker の抽象を MockBrokerClient 等で分離しており、ペーパートレード DB を別に保つことで本番 DB との完全分離を図っている（実際の BrokerClientFactory の実装に依存）。
- DuckDB を分析用途に組み込み（duckdb.connect を使用）。prices_daily / raw_financials 等のテーブルを前提にファクター計算を行う設計。
- ポートフォリオ・ポジションサイジングのロジックはドキュメント（PortfolioConstruction.md / StrategyModel.md）に基づく注釈・ TODO を含む実装になっている（将来的な拡張点をコメントで残している）。

メンテナンス
- 今後の予定: factor_research の残実装完了、SystemMonitor / ExecutionEngine のユニットテスト整備、config/*.yaml の生成スクリプトやドキュメント整備（scripts/generate_config.py を示唆する箇所あり）。

---

この CHANGELOG は、提供されたソースコードの構成・コメント・実装から推測して作成しています。実際の開発履歴（コミットメッセージやリリースノート）を反映していない箇所がありますので、必要に応じて日付や項目を調整してください。