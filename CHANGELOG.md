CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。
タグのないリリースは初期リリースやスナップショットを想定しています。

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- パッケージ初期リリース (バージョン 0.1.0) を追加。
- 基本 CLI / 起動スクリプトを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 DB (data/paper_trading.db) と本番 DB を分離する動作をサポート。停止フラグ・PID 管理・デーモンスレッドでの実行監視を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を使用。
- 環境設定管理:
  - config.py: .env 自動読み込み機能（プロジェクトルート検出に基づく）を実装。厳密な .env パース（export 形式対応、クォートとエスケープ処理、インラインコメント処理など）を行うユーティリティを提供。Settings クラスで設定値をプロパティ経由で取得可能（各種パス、閾値、環境判定ヘルパーを含む）。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。既存 .env の読み込み/編集、セクレット値のマスク、保存機能を提供。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパース確認（PyYAML 未インストール時は YAML 検証スキップ）・本番向けガードチェックなどを行う。
- ロギング／プロセス管理ユーティリティ:
  - utils/logging_setup.py: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに一括設定する setup_logging を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフェイルセーフあり。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows/Linux/macOS の差分を吸収）。権限不足などの失敗は警告ログでスキップ。
- ポートフォリオ構築モジュール（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0時は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知のレジームは警告のうえフォールバック。
  - portfolio/position_sizing.py: ポジションサイズ計算 calc_position_sizes を実装。allocation_method に応じた計算、単元株丸め、per-stock 上限、aggregate cap によるスケーリング（cost_buffer を考慮した保守的見積り）、残差を用いた追加配分ロジック等をサポート。
- 分析 / レポート:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95) を算出し PASS/FAIL 判定 (閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 200ms) を行う。--from/--to/--db オプション対応。
- DuckDB 統合:
  - DuckDB 接続を受け取る設計を各所で採用（実行エンジン / モニタリング / リサーチ系の分析に利用）。
- 監視 DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルを冪等に確保する処理を run_execution/run_monitoring に追加。

Changed
- ログの標準出力先は stdout を採用（cron 等で stdout/stderr を一本化する用途に配慮）。
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- Settings による環境値の検証を強化（有効値チェック・型変換・明示的な例外発生）。
- run_execution の DB 接続は環境に応じて paper_trading 用 DB を分離するよう変更（paper_trading 時は専用 sqlite を利用）。

Fixed
- MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトへフォールバックするようにして time.sleep での ValueError を回避。
- ログディレクトリの作成やファイルハンドラ生成に失敗した場合でも起動継続できるようフォールバック処理を追加。
- process_priority / set_cpu_affinity が権限不足や未対応プラットフォームで例外を投げず警告を出すように改善。

Security
- config_setup.py にて生成される .env ファイルについて「絶対に Git にコミットしないこと」を明記。
- シークレット項目はウィザード表示時にマスクして表示する機能を追加。

Notes / その他
- research/factor_research.py を含むリサーチ系モジュールは、DuckDB を使ったファクター計算の設計に基づく初期実装が含まれる（モメンタム等の計算定義あり）。
- 一部モジュールは他コンポーネント（BrokerClientFactory、ExecutionEngine、SystemMonitor 等）との連携を前提としており、本リリースではインターフェース呼び出し側の参照を含む（実際のブローカークライアント実装等は別モジュールに依存）。
- 初期版のため、今後以下の改善を想定:
  - 単体テストの充実、モジュール分割やドキュメントの細分化
  - 銘柄毎の単元株対応（lot_size を銘柄別に持つ設計への拡張）
  - 不足価格データに対するフォールバックロジックの強化（price_map が欠損時の扱い）

--------------------------------
この CHANGELOG はソースコードの内容から推測して記載しています。実際の変更履歴（コミットログ等）がある場合はそちらに基づき更新してください。