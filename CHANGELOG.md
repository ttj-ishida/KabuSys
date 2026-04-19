CHANGELOG.md

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and the versioning is
managed with SemVer.

v0.1.0 - 初回リリース
--------------------

リリース日: 未設定（初回公開）

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py / run_monitoring.py: 実行エンジンと監視ループの起動スクリプトを追加。共通でプロセス優先度設定、統一ログ設定、SQLite/DuckDB 接続を行う。
    - 監視ループは MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視用 DB を常に本番に向ける設計）。
    - 停止フラグ（data/stop_requested.flag）および pid ファイルを用いた安全な停止処理をサポート。
  - ExecutionEngine 起動時は KABUSYS_ENV=paper_trading の場合に専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と完全に分離する旨を実装。
  - run_execution は BrokerClientFactory、OrderManager、RiskManager（RiskConfig）、Reconciler などを組み立てて ExecutionEngine を起動。

- 設定管理・作成・検証ツールを追加
  - config.py: .env / .env.local 自動読み込み（OS 環境変数が優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース実装は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスに多数のプロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境判定など）および各種値検証。
  - config_setup.py: 対話式ウィザードで .env を初期生成 / 更新する CLI を追加（--env-file で保存先指定可）。秘密値はマスク表示、既存 .env 読み込み対応。
  - validate_config.py: 起動前チェック用 CLI を追加（--strict オプションあり）。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml ファイルの存在および YAML パース（PyYAML がある場合）等をチェック。KABUSYS_ENV=live 向けの追加ガードも含む（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告など）。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 全アプリケーションで共通利用可能なロギング設定を追加。
    - StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次・30 日保持）をファイル出力に設定。
    - LOG_DIR/LOG_LEVEL 環境変数または引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定関数を追加。アクセス権限等で失敗した場合は警告ログを出してスキップ。

- ポートフォリオ構築ロジック（純粋関数群）
  - kabusys.portfolio:
    - portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）。
    - risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。unknown セクター扱いの仕様、レジーム未定義時のフォールバックを実装。
    - position_sizing.py: 各銘柄の株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した配分、端数処理ロジック（残差に基づく追加配分）を実装。

- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成する CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定。
    - DB が存在しない／テーブルがない場合のフォールバック処理を実装。

- データ解析（研究）基盤
  - research/factor_research.py（実装途中を含む）: DuckDB を使った定量ファクター計算の土台を追加（モメンタム、移動平均、ATR、出来高系などを想定）。DuckDB 接続を受け取り SQL + Python で計算する設計。

Changed
- ログ出力の統一化
  - 起動スクリプト群は共通の setup_logging() を呼び出すように変更。ログディレクトリ作成失敗時のフォールバックを明示的に扱うようにした。

- 環境変数読み込みの堅牢化
  - .env のパースを強化（export 形式、クォート・エスケープ対応、インラインコメント処理）。自動ロード順序は OS > .env.local > .env。

Fixed / Robustness improvements
- 起動時の安全対策の追加
  - stop/kill フラグ（data/stop_requested.flag, data/kill.flag）と PID ファイルを用いた安全な起動/停止の仕組みを導入。
  - validate_config の追加により起動前に設定不備を検出可能に。

- DB 初期化の冪等性
  - init_monitoring_db の呼び出しで監視用テーブルが存在することを保証（複数プロセスでの安全性を意識）。

- 異常時のログ出力と例外処理
  - monitor.check_once() 呼び出し中の例外を捕捉してログに出力し、監視ループを継続するようにした（監視プロセスの自己回復性を向上）。

Notes / その他
- バージョン: kabusys.__version__ = "0.1.0"
- .env ファイルは生成時にコミットしない旨を README / config_setup のヘッダに明記している。
- research/factor_research.py は実装途中（ファイル末尾が切れている箇所あり）。今後のリリースでファクター計算ロジックを完成させる予定。
- 一部の設計は将来的な拡張（銘柄毎の lot_size、価格フォールバックの改善など）に備えて TODO コメントを残している。

今後の予定（想定）
- factor_research の完成（各種ファクター算出および標準化ユーティリティとの統合）。
- ExecutionEngine / BrokerClient の詳細実装とそれに伴う統合テスト。
- より詳細な運用ドキュメント（デプロイ手順、監視アラートの設定、Paper→Live 移行手順）。

以上。