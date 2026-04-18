# Keep a Changelog
すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

フォーマットバージョン: 1.0.0

## [Unreleased]
（現状、特定の未リリース変更はありません。実装済みの機能は 0.1.0 にまとめられています）

---

## [0.1.0] - 2026-04-18
初回リリース。以下はこのコードベースで実装された主要な機能・改善・修正のまとめです。

### Added
- 全体
  - パッケージ初期バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - 共通設定オブジェクト `Settings` を提供（src/kabusys/config.py）。.env/.env.local の自動ロード、プロジェクトルート自動検出、必須キーチェックや各種設定プロパティ（DB パス、API トークン、監視閾値、環境種別など）をサポート。

- 環境設定関連 CLI
  - 対話式環境設定ウィザード `kabusys.config_setup` を追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。シークレットは表示マスク、デフォルト値や選択肢を提供。
  - 設定検証ツール `kabusys.validate_config` を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証、`--strict` モードをサポート。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。

- 起動スクリプト
  - 監視プロセス起動スクリプト `run_monitoring` を追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 停止フラグファイルを検知してグレースフルに終了。監視 DB は環境にかかわらず本番 sqlite_path を利用して初期化。
  - 発注エンジン起動スクリプト `run_execution` を追加（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動・監視。プロセス優先度を高く設定し、Paper Trading（KABUSYS_ENV=paper_trading）では MockBroker を用いて paper_trading 用 DB に記録して本番 DB と完全分離。
    - ストップフラグでエンジン停止、PID ファイルの取り扱い、別スレッドで実行して安全に停止を待機。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + 同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重（全銘柄スコアが 0 の場合は等分配にフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクターエクスポージャを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマップし、未知レジームは警告後フォールバック）。
  - 株数決定・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based/equal/score）をサポート。lot_size に合わせた丸め、1 銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと残差配分ロジックを実装。

- ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30 日保持）を一括設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収してプロセス優先度を設定。set_cpu_affinity で先頭 N コアに固定。権限不足や未対応プラットフォームでは警告ログを出してスキップ。

- 分析 / ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。P95 計算や日付フィルタ、DB パス指定オプションをサポート。

### Changed
- .env 読み込み挙動（src/kabusys/config.py）
  - 自動読み込み順序を OS 環境 > .env.local > .env とし、既存 OS 環境変数は保護（上書きされない）する仕組みを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能に。
  - .env 解析を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）して実用性を向上。

- ログ設定（src/kabusys/utils/logging_setup.py）
  - 既存ハンドラを一旦 flush/close してから削除することで複数回初期化した際の二重出力を防止。

- 監視・発注の DB 初期化（run_monitoring / run_execution）
  - 監視用テーブルの初期化（init_monitoring_db）を起動時に冪等に実行してテーブル存在を保証。

- run_monitoring
  - ポーリング中に monitor.check_once() が例外を投げてもループを継続するように例外を捕捉してログ出力を行う安定化処理を追加。

- run_execution
  - Paper Trading モードで専用 SQLite を使用して本番 DB とデータを分離。
  - 停止フラグ検出時の挙動を明確化（起動前に STOP フラグがある場合は起動せず戻る）。

- position_sizing
  - 投資総額が available_cash を超える場合のスケーリング処理で、lot_size 単位での端数処理（残差の大きい順に追加配分）を実装して再現性と公平性を向上。

### Fixed
- .env パーサの不正行ハンドリングを改良し、空行・コメント行・export プレフィックス・クォート付き値・インラインコメントを正しく処理できるように修正（src/kabusys/config.py）。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール出力にフォールバックしてアプリケーションが起動し続けるように修正（src/kabusys/utils/logging_setup.py）。
- process_priority のプラットフォーム差異や権限エラーを捕捉してアプリ側がクラッシュしないよう修正（src/kabusys/utils/process_priority.py）。
- paper_verification_report: データ不足やテーブル未存在時に sqlite3.OperationalError を捕捉してレポート生成を中断しないように改善。

### Security
- シークレット項目（JQUANTS_REFRESH_TOKEN 等）を config_setup の出力や表示で直接露出しないようマスク表示を実施。

### Documentation / Notes
- 各モジュールに docstring を充実させ、設計意図・使用方法・引数仕様・戻り値を明記。
- 一部の TODO コメント（例: price 欠損時の価格フォールバックや銘柄別 lot_size 管理）を残し、将来の拡張点を示唆。

---

今後の予定（参考）
- portfolio/position_sizing: 銘柄別 lot_size をサポートするための設計拡張。
- monitoring / execution: より詳細なメトリクス収集と外部通知（LINE 等）連携の追加。
- research.factor_research の完全実装（ファクター計算ロジックの完成とテスト）。

もし特定部分（例: あるモジュールや関数）に焦点を当てた詳細な変更点一覧が欲しい場合は、対象ファイル名を指定して教えてください。