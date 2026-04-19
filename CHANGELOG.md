CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベースの現在の状態から推測して作成した初期の変更履歴です。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各リリースは バージョン番号 と 日付 を持ち、カテゴリ別（Added / Changed / Fixed / etc.）に記載

Unreleased
----------
（なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション構成とユーティリティを実装
  - Settings クラスによる環境変数の集中管理を追加（src/kabusys/config.py）。
    - 自動的にプロジェクトルートの .env と .env.local を読み込む機能（無効化フラグあり）。
    - 必須値チェック、各種パス（DuckDB/SQLite）、Paper Trading 用の設定等を提供。
    - PAPER_FILL_MODE の妥当性検査を実装。
  - .env の対話式ウィザードでの作成/更新を提供する CLI（src/kabusys/config_setup.py）。
    - 対話入力・既存値再利用・保存機能を備え、.env テンプレートの生成を行う。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース検証。
    - --strict モードで警告を失敗扱いにできる。
  - 実行系（ExecutionEngine）起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - デーモンスレッドでエンジンを起動し、stop フラグ（data/stop_requested.flag）で安全に停止可能。
  - 監視（Monitoring）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグでループ停止、例外はログ出力して次ポーリングへ継続。
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収して set_process_priority, set_cpu_affinity を提供。権限不足や未対応 OS は警告でスキップ。
  - Portfolio 構築用の純粋関数群を追加（src/kabusys/portfolio/*）。
    - 銘柄選定: select_candidates（スコア降順、タイブレークロジック）。
    - 重み算出: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
    - リスク調整: apply_sector_cap（セクター集中制限）, calc_regime_multiplier（市場レジームに応じた乗数）。
    - ポジションサイジング: calc_position_sizes（risk_based / equal / score の投下ロジック、lot 単位丸め、aggregate cap のスケーリング）。
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計・判定ロジックを実装。
    - デフォルト閾値（稼働率 99%、成功率 90% など）を定義し、PASS/FAIL 判定を行う。
    - 日付フィルタリング、P95 計算、各種フォーマット出力を含む。
  - research/factor_research の骨組みを追加（duckdb 接続を受ける設計、モメンタム等の計算方針をドキュメント化）。一部実装は継続中。

Changed
- パッケージの初期バージョンとして公開用メタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

Fixed
- 監視・実行スクリプトでの DB 初期化を冪等に（monitoring テーブルの存在を保証する init_monitoring_db を両方の起動で呼ぶ）。
- logging_setup: 既存ハンドラの二重登録を防ぐため、既存ハンドラを flush/close してから削除する処理を追加。

Security
- .env ファイルの取り扱いに関する注意書きを config_setup の出力に明記（.env を絶対に Git にコミットしない旨）。

Known issues / Notes
- apply_sector_cap: price_map に価格が欠損（0.0）がある場合、セクターエクスポージャーが過少見積りされブロックが外れる可能性がある（TODO を記載）。将来的には前日終値や取得原価でのフォールバックを検討。
- calc_position_sizes:
  - lot_size は現在グローバル固定（例: 100）。将来的に銘柄別単元対応を検討する TODO がある。
  - price が欠損の銘柄はスキップされるため、データ完全性に依存する点に注意。
- validate_config:
  - PyYAML がインストールされていない場合は YAML 検証をスキップして警告を出す挙動。
- research/factor_research は設計方針と定数が記載されているが、ファイル末尾で実装が途中で切れている（継続実装が必要）。

Usage highlights（主な実行方法）
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（または設定の paper_sqlite_path）が使用される
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

参考
- 各モジュールの docstring や TODO コメントに設計意図・今後の拡張案が記載されています。必要に応じて該当ファイルを参照してください（src/kabusys/*）。

---
この CHANGELOG はコードベースの内容から推測して作成しています。差分や追加の履歴が必要であれば、コミット履歴やリリースノートの実データを提供してください。