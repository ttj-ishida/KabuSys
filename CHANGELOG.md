# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はセクション (Added, Changed, Fixed, ...) に分類されています。
- 日付はリリース日に合わせて記載しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買フレームワーク「KabuSys」の主要なモジュール群を実装しました。主な追加点は以下の通りです。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動ループを追加。バックグラウンドスレッドでエンジンを実行し、data/execution.pid に PID を記録する仕組みを提供。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止可能。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグ（data/stop_requested.flag）でループ終了。Monitoring は実行環境にかかわらず本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py
    - .env 自動ロード（プロジェクトルートを .git / pyproject.toml で探索）と堅牢な .env パーサを実装。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、しきい値、環境判定など）をプロパティ経由で提供。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などの環境変数をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。既存値の読み込み、秘密情報のマスク表示、ファイル書き出しをサポート。
  - validate_config.py
    - .env および config/*.yaml の基本的な整合性チェック CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース確認（PyYAML が利用可能な場合）などを実施。--strict オプションをサポート。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を統一的に設定。
    - 環境変数 LOG_LEVEL / LOG_DIR に対応。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py
    - psutil を利用して Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity を提供（利用できない環境では警告を出してスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全体が 0 の場合のフォールバック等を考慮。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた資金乗数を返す calc_regime_multiplier を実装。未知のレジーム時にはフォールバックと警告を出す。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score の割当方式）を実装。単元株（lot_size）丸め、max_position_pct、max_utilization、コストバッファ、aggregate cap（利用可能現金によるスケールダウン）の処理などを実装。スケーリング時の端数配分アルゴリズムを備える。
  - portfolio/__init__.py
    - 上記関数群をパッケージの公開 API としてエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読んでレポートを生成する CLI を実装。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどの指標を算出し、閾値比較で PASS/FAIL 判定を行う。
    - データが存在しない場合の安全な処理や、クエリ失敗時のフォールバックを考慮。
- 研究モジュール（基礎実装）
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタム、ボラティリティ、バリュー等のファクターを計算するための骨格を追加（モメンタム計算などの定数・設計方針を含む）。※ファイル末尾に未完の実装箇所あり（継続実装予定）。
- パッケージメタ
  - __init__.py にてバージョン番号を設定 (__version__ = "0.1.0")。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報は .env に保存する設計とし、config_setup の出力内で「.env は絶対に Git にコミットしないこと」を明記。

---

注記・設計上のポイント
- DB 関連
  - Monitoring 用の SQLite（settings.sqlite_path）は監視機能が常に本番 DB を読み書きするように設計されていますが、Execution は KABUSYS_ENV により paper_trading 用 DB と本番 DB を分離します（settings.is_paper 判定に依存）。
  - DuckDB は分析用の永続 DB として統合され、複数コンポーネントから接続して使用します。
- ロギング
  - コンソールは stdout へ出力することで cron 等でのログリダイレクトを容易にしています。ログファイルは日次ローテーションで保管しますが、ログディレクトリの作成に失敗した場合はコンソールへの出力のみで継続します。
- 安全停止
  - 起動スクリプトはいずれもプロセス外からの停止フラグ（data/stop_requested.flag）を監視し、安全にシャットダウンする仕組みを備えています。
- 設定の堅牢性
  - .env パーサは quote やエスケープ、inline コメントの取り扱いに配慮した実装になっており、OS 環境変数を保護する仕組み（protected keys）も提供します。
- 未実装 / TODO
  - research/factor_research.py の関数実装の続き（ファクター計算の SQL 実装等）。
  - position_sizing の lot_size を銘柄単位で扱うための拡張（将来的には銘柄マスタとの連携を予定）。
  - いくつかの TODO コメントに示したフォールバック価格ロジック等は今後の改良予定です。

---

作成者: KabuSys コアチーム（コードベースから自動生成・推測）  
備考: 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴・変更履歴と完全に一致しない場合があります。