CHANGELOG
=========
このファイルは Keep a Changelog の形式に準拠しています。  
リリース日付はコードベースの最終編集日（2026-04-24想定）で記載しています。

v0.1.0 — 2026-04-24
-------------------

Added
- 初回リリース: パッケージ基本構成を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 起動スクリプト / 実行フロー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path (= data/paper_trading.db デフォルト) を使用して本番 DB と完全分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動するワークフローを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を用いた安全停止処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - stop フラグ検知、例外ハンドリング、リソースクローズ処理を実装。
- 設定・環境変数管理
  - config.py: Settings クラスによる環境変数ラッパーを実装。
    - .env 自動ロード機能（.env → .env.local、OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパースは export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメント等に対応。
    - 各種設定プロパティ（J-Quants、kabu API、DB パス、監視閾値、環境判定など）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 各設定項目のプロンプト、既存 .env 読み込み、シークレットマスク表示、保存機能を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 等の妥当性チェック、DB パスや config/*.yaml の存在検査、live 環境向けガードを実装。
    - --strict オプションで警告を fail 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler、30日保持）。
    - LOG_LEVEL と LOG_DIR の解決順、ハンドラ二重登録防止、ディレクトリ作成失敗時のフェールオーバー処理を実装。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収して優先度設定（high/normal/low）を提供。
    - CPU affinity を最初の N コアに固定する関数も実装。パーミッション不足時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純関数）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、コストバッファ考慮を実装。
  - portfolio/risk_adjustment.py
    - セクター上限適用（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier）を実装。
  - portfolio/__init__.py でまとめてエクスポート。
- Paper Trading 用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。コマンドラインで期間指定可能。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出して、監視テーブルの存在を保証する仕組みを採用（冪等）。
- リサーチ（部分実装）
  - research/factor_research.py: モメンタム等のファクター計算モジュールを追加（DuckDB を用いた prices_daily / raw_financials 参照の方針）。Momentrum 計算のための定数類と関数 calc_momentum の雛形を含む（実装継続中）。

Changed
- 環境 LOAD の優先度と保護
  - OS 環境変数を保護するため .env 自動ロード時に protected set を使って既存の OS 環境変数を上書きしない挙動を採用。
- 実行時の DB 選択ルールを明確化
  - run_monitoring は常に sqlite_path（本番監視 DB）を使用する仕様。run_execution は is_paper によって paper_sqlite_path を切り替える。

Fixed
- .env パーサ: export プレフィックス、クォート内エスケープ、行内コメントの扱いに対応し、より堅牢な .env 読み込みを実現。

Notes / Known issues
- research/factor_research.py は一部で実装が途中（ファイル末尾が切れている／途中行あり）。今後の PR で完了予定。
- 一部の機能（ブローカークライアント、ExecutionEngine 本体、SystemMonitor 実装、monitoring_db の詳細など）はこの差分には含まれておらず、別モジュールとして存在する想定。実際の運用前にそれらの結合テストを推奨します。
- process_priority と cpu_affinity の設定は OS 権限や psutil のサポートに依存します。権限不足時は警告を出して安全にフォールバックします。
- デフォルト値（ログディレクトリ、DB パス等）は data/ や logs/ を使用するため、運用環境では適切なパスとパーミッションの確認を推奨します。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）で制御するため、運用用に stop フラグの管理・クリア方針を運用手順に記載してください。

Security
- 重要なシークレット（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は .env に保存する設計のため、.env を絶対にリポジトリにコミットしない旨を config_setup.py のヘッダに明記。

今後の予定（短期）
- research/factor_research.py の完了（Momentum の SQL 実装など）。
- ExecutionEngine / SystemMonitor の統合テスト、運用向けドキュメント整備（デプロイ手順、監視・アラート設定）。
- 単体テスト追加（.env パーサ、ポートフォリオ計算、position sizing の corner case 等）。
- paper_trading のシミュレーション結果を自動で集計する CI スクリプト等の追加検討。

---
（補足）本 CHANGELOG は提供いただいたソースコードから推測して作成しました。実際の変更履歴やリリースノートは実際のコミット履歴・開発ノートに基づいて確定してください。