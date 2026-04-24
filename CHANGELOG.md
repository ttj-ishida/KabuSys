# Changelog

すべての変更は Keep a Changelog 準拠の形式で記載しています。主な機能追加・改善点を日本語でまとめています。

v0.1.0 - 2026-04-24
-------------------

Added
- 初期公開: KabuSys パッケージの主要機能を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用し、本番 DB と分離して動作するよう実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag による。
- 設定管理
  - config.py: .env 自動読み込み機能（.env, .env.local）を追加。プロジェクトルート自動検出（.git または pyproject.toml 基準）。Settings クラスを導入し、環境変数取得とバリデーションを集約（KABUSYS_ENV / LOG_LEVEL 等の検証、PAPER_FILL_MODE の有効値チェックなど）。
  - config_setup.py: 対話式 .env ウィザードを追加し、.env の作成・更新を簡便化。
  - validate_config.py: 起動前の設定検証 CLI を追加 (.env や config/*.yaml の存在/妥当性チェック、--strict オプション対応)。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加（コンソール stdout と TimedRotatingFileHandler による日次ログローテーション、LOG_DIR/LOG_LEVEL の解決順をサポート）。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows / POSIX 対応、アクセス権限失敗時は警告でフォールバック）。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等配分・スコア重み生成(calc_equal_weights, calc_score_weights)を追加。スコア全0時は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限の適用(apply_sector_cap)と市場レジームに応じた投下資金乗数(calc_regime_multiplier)を追加。
  - portfolio/position_sizing.py: 発注株数算出ロジック(calc_position_sizes)を追加。risk_based / equal / score 各方式、単元株丸め、aggregate cap によるスケールダウン、手数料・スリッページ見積り用の cost_buffer を考慮。
  - portfolio/__init__.py: 上記 API をエクスポート。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを計算して PASS/FAIL 判定を行う。コマンドライン引数で期間指定・DB 指定が可能。
- 研究モジュール（骨格）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム・ボラティリティ等の計算方針を実装）。（注: ファイル末尾は実装継続中の箇所あり）

Changed
- DB 周りの設計
  - duckdb を分析用 DB として導入（Settings.duckdb_path）。分析処理と監視・発注履歴用 SQLite を用途に応じて使い分け。
  - run_monitoring は monitoring 用に Settings.sqlite_path の本番パスを常に使用する仕様に（環境に依存しない監視用 DB）。
  - run_execution は paper_trading モードで専用 paper_sqlite_path を使用し、実運用 DB と完全に分離する挙動を採用。
- 環境変数読み込みの仕様
  - .env パーサを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、およびインラインコメント処理に対応）。
  - OS 環境変数を保護する protected オプションを導入し、.env.local による上書き動作を制御。
  - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- ログ出力仕様
  - StreamHandler は stdout を使用（stderr ではない）。ログファイルは日次ローテーションで最大30日保持。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定し、二重設定を防止。
- 起動時のプロセス優先度
  - run_monitoring/run_execution で起動直後に set_process_priority("high") を呼ぶようにした（高優先度での実行を推奨）。
- モニタリング・停止制御
  - 起動中の停止は data/stop_requested.flag を検知して安全終了する仕組みを導入。ExecutionEngine 用に execution.pid を生成する想定（PID ファイル取り扱いを Settings で抽象化）。

Fixed
- 環境変数パースの堅牢化: _parse_env_line でクォート内エスケープやコメント処理を正しく扱うよう改善し、誤った .env 行による読み込みエラーを軽減。
- MONITOR_POLL_INTERVAL の解析で 0 以下や不正値が指定された場合にデフォルトへフォールバックする処理を追加（警告出力付き）。
- .env の読み込みでファイルアクセス失敗時に警告（warnings.warn）を出してスキップするように改善。

Security
- 必須機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings で取得時に未設定なら明示的に例外を投げるようにして、起動時に不足を検知しやすくした。
- .env の生成テンプレートに「.env を絶対に Git にコミットしないこと」という注意書きを追加。

Notes / Internal
- validate_config.py は config/*.yaml の存在チェックと PyYAML があれば内容のパース検証も行う。ただし PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
- portfolio/position_sizing のロジックは将来的に銘柄別 lot_size の導入を考慮した拡張性を持たせている（TODO コメントあり）。
- process_priority.set_cpu_affinity はプラットフォーム差異により失敗する可能性があり、その場合は警告でフォールバックする設計。
- research/factor_research.py はファクター計算方針と定数が定義されており、DuckDB を用いた実装の続きが見込まれる。

既知の制限
- research/factor_research.py の一部実装が途中で終わっている（ファイル末尾の続きが必要）。
- 実際のブローカークライアントや ExecutionEngine の細部はここに含めた起動スクリプトから呼び出される想定だが、外部依存（kabuステーションや J-Quants など）の接続周りは運用環境での設定が必要。

今後の予定（参考）
- research/factor_research の完実装（duckdb ベースの SQL 実行部分）。
- より詳細なテストと CI の追加、ドキュメント整備（運用手順、環境変数の説明など）。
- 銘柄別 lot_size 対応やより高度なポジション調整アルゴリズムの導入。

----- 

このリリースでは初期の CLI・設定周り、ロギング/プロセス管理ユーティリティ、ポートフォリオ構築ロジック、およびペーパートレード検証ツールなど、KabuSys のコアとなる基盤機能を整備しました。ご不明点や追記して欲しい変更点があればお知らせください。