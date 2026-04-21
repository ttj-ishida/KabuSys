CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。
リリースノートは後方互換性や運用上の重要点を中心に記載しています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-21
------------------

Added
- 初期リリースを公開。
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。起動時にプロセス優先度を "high" に設定し、スレッドでエンジンを実行、停止フラグ・PID ファイル対応を実装。paper_trading 環境では専用の MockBroker と paper_trading.db を使用して本番 DB と完全に分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理・検証・ウィザード
  - config.py: Settings クラスを実装。.env 自動ロード（.env → .env.local、OS環境変数優先）・各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV、paper_trading 用設定等）を提供。PAPER_FILL_MODE のバリデーション等を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（秘密値マスク、デフォルト値、選択肢サポート、保存機能）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスと config/*.yaml の存在チェック、--strict モード（警告を FAIL 扱い）をサポート。
  - .env パースの強化: export プレフィックス、クォート値のエスケープ、コメントの扱いなどに対応する堅牢なパーサを実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール出力は stdout を使用し、TimedRotatingFileHandler（日次ローテーション、30 日保持）をサポート。既存ハンドラのクリア処理を実装。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加（Windows / POSIX を吸収、権限不足等は警告でスキップ）。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と基本的な重み計算（等分配、スコア加重）を追加。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）を実装。未知レジームや unknown セクターに対するフォールバック動作を定義。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score 対応）、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、各種リスクパラメータをサポート。
  - portfolio/__init__.py で API をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。日付フィルタ、P95 計算、閾値判定を実装。
- Research (ファクター計算) のスケルトン
  - research/factor_research.py: モメンタム等のファクター計算モジュールの骨組み（DuckDB 接続を受け取って prices_daily 等を参照する設計）を追加（一部未完の実装あり）。
- パッケージメタ
  - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- ログ出力の標準化: ログのコンソール出力に stdout を使用して、cron 等の出力リダイレクト運用を容易化。
- .env 自動ロードの挙動: プロジェクトルート検出（.git または pyproject.toml）に基づき .env を読み込むように変更。KABUSYS_DISABLE_AUTO_ENV_LOAD によって自動ロードを無効化可能。
- 実行・監視の起動時に優先度を最初に上げることで運用中の応答性・優先度を保証。

Fixed
- 環境変数の境界値処理を追加
  - MONITOR_POLL_INTERVAL が不正（数値でない、0 以下など）の場合はデフォルト（60 秒）にフォールバックして警告を出すように変更。
  - calc_score_weights: 全銘柄スコアが 0 の場合に等分配へフォールバックするよう修正（ゼロ除算回避）。

Security
- 機密情報取り扱い
  - config_setup の出力ではシークレット項目をマスクして表示。
  - .env は README や出力にて Git へのコミット禁止を明記。

Notes / 補足
- 実行環境保護
  - validate_config は KABUSYS_ENV=live の場合に本番ガード（LINE 設定不足、KILL_FLAG_CLEAR_ON_START の危険設定等）を警告するチェックを含みます。運用では validate_config による事前チェックの実行を推奨します。
- DB の使い分け
  - run_execution は paper_trading 環境であれば paper_trading 用 SQLite を使用し、本番 monitoring DB とデータを分離します。一方 run_monitoring は監視データのため本番 sqlite_path を環境にかかわらず参照します（監視データを一元化する設計）。
- 一部モジュール（research/factor_research.py 等）は設計方針と入出力仕様を備えた骨組みが含まれ、一部処理が未完のため実運用前に追加実装が必要です。

今後の改善候補（非網羅）
- position_sizing の銘柄別 lot_size 対応（現在は共通 lot_size）。
- apply_sector_cap の price 欠損時のフォールバック（前日終値等）。
- factor_research の完全実装と単体テスト整備。
- ログのリテンションやフォーマッタ設定の更なる柔軟化（環境変数/設定ファイルから変更可能に）。

---