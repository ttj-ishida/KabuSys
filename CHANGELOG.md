CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。  
リリース日付はコードから推測可能な最新の状態（2026-04-18）で記載しています。

Unreleased
----------

（今後の変更はこちらに記載してください。）

0.1.0 - 2026-04-18
-----------------

Added（追加）
- 初回公開: KabuSys 自動売買フレームワークの実装を追加。
- 実行スクリプト
  - run_monitoring.py: システム監視用ポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルート/data/stop_requested.flag によるフラグで行う。監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db）に完全分離して記録する。実行中は PID ファイル管理と停止フラグ監視を行う。
- 環境/設定管理
  - config.py: .env ファイルの自動読み込み（.env → .env.local 優先）、.env パースの堅牢化（export プレフィックス、クォート／エスケープ、インラインコメント処理等）。環境変数の必須チェック用ユーティリティを提供（Settings クラス）。
  - config_setup.py: .env 作成・更新の対話式ウィザード（複数設定項目、シークレット入力や既存値の再利用をサポート）。.env ファイルテンプレート出力を実装。
  - validate_config.py: 起動前チェック CLI。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在/パース・本番時のガード（LINE 通知設定や Kill Switch の自動クリア）などを検証。--strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。ログディレクトリ作成で失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定（Windows/Linux/macOS の差分吸収）、CPU affinity 設定ユーティリティ。アクセス権限例外は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全てが 0 の場合に等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知のレジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）丸め、1銘柄上限、aggregate cap に基づくスケーリング、cost_buffer を使った保守的見積り、残差配分ロジックを実装。
- 解析・調査ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などの集計と PASS/FAIL 判定（閾値をコード内で定義）。--from/--to/--db オプションをサポート。
- research/factor_research.py（開始実装）
  - DuckDB を用いたファクター計算基盤（モメンタム・ATR 等を想定）。設計方針と定数を実装（モメンタム計算等の関数実装が進行中）。

Changed（変更）
- なし（初回公開のため変更履歴はありません）。

Fixed（修正）
- なし（初回公開のため修正項目はありません）。

Deprecated（非推奨）
- なし。

Removed（削除）
- なし。

Security（セキュリティ）
- 環境変数の扱いに注意を促すメッセージをウィザード・設定検証に追加（.env は絶対に Git にコミットしないこと等）。機密値はウィザードでマスク表示。

Notes / 実装上の注記
- run_monitoring: 監視は監視用 DB 初期化（init_monitoring_db）を行うが、ドキュメント注記通り monitoring は常に settings.sqlite_path（本番の sqlite_path）を利用する設計のため、本番/開発の DB 分離に注意が必要。
- run_execution: paper_trading 環境では settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離するように設計されている。
- config.py の自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行う。CWD に依存せず配布後も動作することを意図している。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- utils/logging_setup はログディレクトリの作成失敗時にファイル出力を安全にスキップする実装。これにより初回起動や権限のない環境でも標準出力で動作する。
- portfolio/position_sizing の aggregate cap スケーリングは小数切り捨てと残差再配分を組み合わせており、lot_size（単元）に整合するよう配慮されている。
- config パーサ（_parse_env_line）は export 句、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮しており、従来の単純実装より堅牢。

今後の作業候補（提案）
- research/factor_research の関数実装完了とユニットテスト追加。
- 各モジュールのユニットテスト、CI ワークフロー整備。
- ロギング設定の単体テスト（ディレクトリ作成失敗時の挙動など）。
- 監視／実行コンポーネントの統合テストおよび Docker 化サポート。

--- 
（この CHANGELOG はコードベースの内容を元に推測して作成しています。実際のコミット履歴とは異なる場合があります。）