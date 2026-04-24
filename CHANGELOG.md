CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)
※ 日付はリリース日を示します。

Unreleased
----------
- なし

[0.1.0] - 2026-04-24
--------------------
Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を介した分離された検証が可能。バックグラウンドスレッドでセッションを実行し、data/stop_requested.flag による停止、PID ファイル(data/execution.pid) の管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。停止フラグによる安全な終了と KeyboardInterrupt のハンドリングを実装。

- 設定管理・初期化ツール
  - config.py: .env 自動読み込み機能を実装（.env, .env.local の順、OS 環境変数を保護）。.env パースの強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなど）。Settings クラスを通じた型付きプロパティを提供（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 等）。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を追加。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。複数の設定項目（実行環境、API トークン、DB パス、ログレベル、Kill Switch など）をサポートし、シークレット項目はマスク表示。保存前の確認プロンプトを実装。
  - validate_config.py: 起動前に .env と config/*.yaml の不備を検出する検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML の存在と（PyYAML がインストールされている場合の）パース検証、本番ガード（KABUSYS_ENV=live 時の追加警告）等を実装。--strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス優先度ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート・30日保持）を設定する共通セットアップを追加。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py: psutil を使ったクロスプラットフォームのプロセス優先度設定機能を追加。Windows / POSIX（Linux, macOS 等）の差分を吸収し、CPU affinity を設定する関数も提供。アクセス権不足や未対応 OS でのフォールバック・警告処理を実装。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を追加。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存ポジションを考慮して新規候補を除外）と市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジーム時のフォールバックと警告を追加。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に基づく株数計算と単元株丸め、1 銘柄上限・集計上限のスケーリング、手数料等を見積もる cost_buffer による保守的な見積りロジックを実装。価格欠損時のスキップや lot_size 単位での残余配分アルゴリズムも導入。

- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite データを集計して検証レポートを出力するユーティリティを追加。稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出し、所定の閾値と比較して PASS/FAIL を判定可能。コマンドライン引数で期間指定と DB パス上書きに対応。

- 研究モジュール（下地）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / 出来高系などを想定）。関数 calc_momentum の実装開始と定数定義。

Changed
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を追加。主要サブパッケージを __all__ で公開。

Fixed
- 環境変数・設定ロードの堅牢性向上
  - .env の読み込みに失敗した場合に警告を出して継続するように変更（テストや CI での取り扱いを考慮）。
  - .env パーサーでクォート内のエスケープやコメント処理を改善し、誤ったパースによる設定ミスを軽減。

Notes / Implementation details
- 停止フラグ / Kill Switch
  - run_*.py スクリプトはプロジェクトルート下の data/stop_requested.flag を監視し、存在時に安全にシャットダウンする方式を採用。KILL_FLAG_CLEAR_ON_START（Settings）により起動時に Kill Flag を自動クリアする挙動が制御可能（本番では無効推奨）。
- データベース
  - DuckDB は分析用に使用（settings.duckdb_path）。監視・トレードログ等は SQLite（settings.sqlite_path / settings.paper_sqlite_path）で管理。監視用テーブルの初期化関数 init_monitoring_db を起動時に冪等で呼び出している。
- フォールバックと安全策
  - ログディレクトリ作成失敗、プロセス優先度変更失敗、CPU affinity 未対応等のケースは警告を出して処理をスキップする設計になっており、サービスが致命的に停止しないよう配慮している。
- バリデーション
  - Settings による環境値チェックは起動時の早期検出を目的としており、不正な値（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）は ValueError を発生させる。

今後の予定（提案）
- research/factor_research.py の各ファクター計算の完成とユニットテスト追加
- execution の各コンポーネント（ExecutionEngine, OrderManager, RiskManager, Reconciler 等）のドキュメント化と入出力テスト
- モニタリング・アラート（LINE 通知等）の統合テストと設定ガードの強化
- 単体テスト・統合テストの追加と CI パイプラインへの組み込み

---