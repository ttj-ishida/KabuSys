# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

最新リリース
--------------

### [0.1.0] - 2026-04-24
初回リリース。以下の主要機能・ユーティリティを追加しました。

Added
- 実行・監視起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db）を使用し、MockBrokerClient を使う想定。PID ファイル管理、停止フラグ監視、スレッドでのエンジン実行制御を実装。
  - run_monitoring.py: SystemMonitor 起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
- 設定管理
  - config.py: 環境変数/.env の自動読み込みロジック、.env 行パーサ（export 形式・クォート・エスケープ・インラインコメント対応）、Settings クラス（各種環境変数プロパティ）を追加。環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE、パス等）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加（選択肢・シークレット入力・保存確認）。.env の読み書きロジックを実装。
  - validate_config.py: 起動前に .env および config/*.yaml の設定不備を検出する検証 CLI を追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML がない場合は YAML 検証をスキップする柔軟性あり。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定関数 setup_logging を追加。stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定、ログディレクトリ自動作成・フォールバック処理を実装。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）、および CPU affinity 設定関数を追加。アクセス権限や未対応 OS 時のフォールバックと警告を実装。
- ポートフォリオ関連モジュール（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック動作を実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームのフォールバックとログ出力あり。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株丸め、1 銘柄上限・総投下上限（aggregate cap）・cost_buffer を考慮したスケーリングを実装。lot_size 固定（将来的な拡張を TODO として明記）。
  - portfolio/__init__.py: 上記関数群をエクスポートするモジュール。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading SQLite DB（デフォルト: data/paper_trading.db）から指標を集計し、稼働率・注文成功率・送信率・レイテンシ（P95）などを計算してレポート出力する CLI を追加。閾値による PASS/FAIL 判定を実装。
- 研究用ファクター計算（下地）
  - research/factor_research.py: DuckDB 接続を受け取り、モメンタム等のファクターを計算するための設計および定数を追加（モジュール骨格と calc_momentum の冒頭を実装）。（注: 大規模なファクター計算ロジックは継続実装予定）

Changed
- なし（初回リリースのため該当なし）

Fixed
- なし（初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

注意事項・既知の制約
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_monitoring は監視 DB に対して「環境にかかわらず本番 sqlite_path を使用する」設計。運用上の注意が必要。
- Paper Trading と本番 DB は意図的に分離される設計だが、設定ミスでパスが指し示す先が同一になっていないか事前に validate_config で確認することを推奨。
- research/factor_research.py のファイル末尾で実装が途中の箇所が含まれます。ファクター計算の完全な実装は今後のリリースで追加予定です。
- position_sizing の lot_size は全銘柄共通で固定（将来的に銘柄別単元対応を検討）。

今後の予定（例）
- research モジュールの各ファクター計算（Momentum/Value/Volatility/Liquidity）の完成
- ExecutionEngine や Broker の具体実装（テスト用モックの改善とインタフェース安定化）
- 単元株・証券マスタ情報を取り込んだ position_sizing の拡張
- モニタリング・アラート（LINE）連携の充実化

ライセンス・その他
- このリポジトリのバージョンはパッケージ定義の通り __version__ = "0.1.0" です。

（必要に応じて、今後のコミットに合わせて Unreleased セクションを追加してください。）