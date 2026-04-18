CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — and is maintained in
Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーションモジュールを追加
  - kabusys パッケージの初期リリース（__version__ = 0.1.0）。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録する。実行中は data/execution.pid を使用し、data/stop_requested.flag による外部停止に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視開始時にプロセス優先度を高く設定し、停止フラグで安全終了する。
- 環境設定関連 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新するツールを追加（各種設定項目、シークレット入力、デフォルト表示、保存確認）。
  - validate_config.py: .env と config/*.yaml の整合性チェック CLI を追加。必須環境変数の存在、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパース確認（PyYAML があればパースする）などを行う。--strict オプションで警告を失敗扱いにできる。
- 環境変数読み込み機能強化
  - config.py:
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
    - .env / .env.local 自動ロード機能を追加（OS 環境変数を保護しつつ .env.local は上書き可能）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを実装し、各種設定（DB パス、紙トレード用設定、監視閾値、PID/kill flag パス、環境フラグ等）をプロパティとして提供。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度（high/normal/low）設定と CPU affinity 設定を追加。Windows / POSIX の差分を吸収し、権限不足や未対応環境では警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py: シグナルのソート（score 降順、タイブレークに signal_rank）と候補選定、等金額 / スコア加重の重み計算を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数計算（calc_regime_multiplier）を実装。unknown セクター扱いやログ出力あり。
  - portfolio/position_sizing.py: 単元丸め、リスクベース / equal / score の配分ロジック、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと端数処理を実装。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- 研究・指標計算
  - research/factor_research.py: DuckDB 接続を受け取り、モメンタム / MA200 乖離 / ATR / 出来高等のファクター計算を行うモジュールを追加（設計ドキュメント参照の意図を記載）。※ファイル末尾は一部未完の箇所あり（calc_momentum の実装継続を想定）。
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から稼働率・注文成功率・送信率・API レイテンシ等を集計し、PASS/FAIL 判定を行うレポート生成スクリプトを追加。期間フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。既定の判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。P95 算出や欠損ハンドリングを実装。
- SQLite / DuckDB 統合
  - run_execution.py / run_monitoring.py で sqlite3 および duckdb 接続を確立し利用。監視 DB 初期化関数 init_monitoring_db を呼び冪等に監視テーブルを準備。

Changed
- 監視プロセスの DB 選択挙動
  - run_monitoring.py はドキュメント通り、KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを記録する挙動を採用（監視は本番 DB を対象とする設計）。運用時の注意点として明記。
- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む仕様を導入（.env.local は OS 環境変数を保護しつつ上書き可能）。
- ロギング設定の耐障害性向上
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でもコンソール出力は継続し、詳細は警告で通知する。
- ExecutionEngine 起動フロー
  - paper_trading 環境では paper 用専用 SQLite を使い完全分離することで本番 DB への影響を回避。
- process_priority の互換性
  - Windows / POSIX の違いを吸収し、権限不足や未実装メソッドに対しては警告を出して処理をスキップするように変更。

Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントなどを考慮して .env 行を正しくパースするように修正。空行やコメント行のスキップ等も適切に処理。
- 監視 DB 初期化の冪等性
  - init_monitoring_db を呼び出して監視テーブルの存在を保証することで、複数回起動しても安全にテーブル準備されるようにした。
- スレッド終了・停止検知の安全化
  - run_execution.py の実行スレッドループで外部停止フラグ検知時に engine.stop() を呼んで安全にシャットダウンする実装を追加。停止フラグ検知時は起動をスキップする早期戻りも実装。
- レポート生成の欠損データ対応
  - paper_verification_report.py で該当テーブルが存在しない、またはデータ不足時に例外を潰して N/A 表示・FAIL 判定を行う耐障害性を追加。

Security
- なし

Notes / 注意事項
- run_monitoring.py の挙動は設計上「監視は常に本番用 sqlite_path を使う」ため、監視データが本番 DB に書き込まれます。開発環境で監視を分離したい場合は別途監視用 DB を指定する等の対処が必要です。
- research/factor_research.py の calc_momentum 関数以降はソース末尾で実装継続の痕跡があり、完全実装を必要とする機能が残っている可能性があります（将来的な追加実装予定）。
- .env は機密情報を含むため決して Git にコミットしないこと（config_setup.py のヘッダにも注意書きを記載）。

---------- 

本 CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートとして公開する前に、各項目の正確性をソース管理履歴と照合してください。