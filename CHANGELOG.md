CHANGELOG
=========

この変更履歴は「Keep a Changelog」（https://keepachangelog.com/）に準拠して記載しています。  
コードベースの内容から推測して作成しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys 基本モジュール群を追加。
  - 環境設定・読み込み
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git / pyproject.toml 基準）。
    - .env パース機能（export 形式、シングル/ダブルクォート、インラインコメント考慮）。
    - Settings クラスを導入し、各種環境変数（J-Quants / kabu API / DB パス / LOG_LEVEL 等）をプロパティ経由で取得・検証。
  - 設定ユーティリティ・CLI
    - config_setup: 対話式ウィザードで .env を生成/更新する CLI を実装。
    - validate_config: .env と config/*.yaml の事前検証を行う CLI（--strict オプション対応）。
  - 実行系ランナー
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用（Mock）ブローカを使用し、paper_trading 用 SQLite（data/paper_trading.db）に分離される挙動を実装。
      - エンジンの PID ファイル、停止フラグ（data/stop_requested.flag）監視、スレッド実行/停止制御を実装。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は本番 sqlite_path を環境にかかわらず使用する旨の設計。
      - 停止フラグ検出でループを終了する実装。
  - DB / モニタリング
    - init_monitoring_db: 監視用テーブルが存在することを保証する初期化処理（冪等）。
    - SQLite / DuckDB 接続を受け取る設計（実行・監視で共通利用）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定・重み算出（select_candidates, calc_equal_weights, calc_score_weights）。
    - portfolio.position_sizing: 各銘柄の発注株数算出（risk_based / equal / score、lot_size, cost_buffer, aggregate cap スケーリング等を実装）。
    - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。
  - 実行系コンポーネント（組立ての痕跡）
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等の呼び出し／組立てロジックを実装（run_execution での連携を想定）。
    - RiskManager にデフォルト RiskConfig を設定し、broker.get_available_cash() を初期ポートフォリオ値に用いる実装。
  - ロギング・プロセス制御ユーティリティ
    - utils.logging_setup: root ロガーに対して StreamHandler（stdout）および TimedRotatingFileHandler（日次・30日保持）を統一設定するユーティリティを実装。ログレベル・ログディレクトリの解決順を定義。
    - utils.process_priority: プラットフォーム差を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。起動スクリプトが早期に優先度を高くする呼び出しを行う。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを実装。
      - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL を出力。
      - デフォルト閾値（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
  - パッケージ情報
    - パッケージバージョンを __version__ = "0.1.0" に設定。

Changed
- 初期挙動設計に関する注意点を明記。
  - run_monitoring は KABUSYS_ENV にかかわらず「本番用 sqlite_path」を使用する仕様（意図的な分離方針）。
  - logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップして stdout のみで継続するフォールバックを実装。
  - process_priority はサポート外 OS に対しては警告を出してスキップする安全設計。

Fixed
- init_monitoring_db を監視・実行の双方で呼び出すことで、監視テーブルが存在しないケースでの起動失敗を回避（冪等に初期化）。

Known issues / Notes
- research.factor_research モジュールはモメンタム等のファクター計算を実装中（ファイル末尾が途切れている/未完部分あり）。完全実装は今後の作業予定。
- 一部の箇所で TODO コメントあり:
  - position_sizing / apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）を将来的に検討する旨の注記。
- テストコード・CI 設定はコードベースに含まれていないため、実運用前に追加の自動テスト・統合テストを推奨。
- 設定値（例: PAPER_FILL_MODE 等）の不正値に対する検証は行われるが、運用時のデフォルト振る舞い（特に paper_trading モード）を十分に確認してください。

Security
- 機密情報（J-Quants リフレッシュトークン、Kabu API パスワード等）は .env に格納する設計。config_setup にも「.env を絶対に Git にコミットしない」旨の注意書きを明記。

Contributors
- 初期実装（この CHANGELOG はコードの解析に基づく推測記述です）。

----- 

注: 本 CHANGELOG は与えられたコードの内容から推測して作成しています。実際のコミット履歴や意図されたリリースノートと差異がある可能性があります。必要であれば、実際の git 履歴や追加情報に基づいて調整します。