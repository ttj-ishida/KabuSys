CHANGELOG
=========

この CHANGELOG は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で記述しています。  
このファイルはコードベースから推測して作成した変更履歴です。実際のコミット履歴と差異がある場合があります。

Unreleased
----------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤実装を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite(DB) を使用し、本番 DB と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ (data/stop_requested.flag) を検知して安全に終了。
- 設定・環境管理
  - config.py: .env 自動読み込み（OS > .env.local > .env の優先順位）、プロジェクトルート自動検出、各種設定プロパティを提供（DB パス、API トークン、Paper Trading 設定、監視閾値など）。
  - config_setup.py: .env の対話式ウィザード。既存 .env 読み込み、シークレットマスク、保存用テンプレート生成をサポート。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML がなければ警告）。
- 実行・監視関連
  - monitoring/monitoring_db の初期化呼び出し（監視テーブルの存在を保証、冪等）。
  - Execution 側: BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/Reconciler/ExecutionEngine の組み立てと実行。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみ継続するなどフォールバック処理を実装。
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティ。権限不足や未対応 OS に対するフォールバック処理を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア順、タイブレーク）、等金額配分、スコア加重配分（スコア総和が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（指定比率を超えるセクターの候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、1 銘柄上限・aggregate cap、cost_buffer による保守的見積り、スケーリングと残差配分ロジック。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシなどを計算・判定してテキスト出力。期間フィルタ、DB パスの引数/環境変数対応。テーブル欠如時の安全ハンドリングあり。
- 研究モジュール（スケルトン）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格（モメンタム/MA/ATR 等の定数と設計方針を定義、実装を開始）。

Changed
- 環境変数読み込みの改善
  - .env パーサで export KEY=val 構文やクォート文字列内のエスケープ、インラインコメントの扱いをサポート（より実用的な .env 読み込み）。
  - OS 環境変数は保護され、.env の上書き制御 (override/protected) を導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト等向け）。
- ロギングのデフォルト挙動を明確化
  - デフォルトでは stdout に出力し、ログファイルを logs/<app_name>.log として日次ローテーションで保存。ログディレクトリが作成できない場合もプロセスは継続する。
- run_monitoring/run_execution の起動シーケンス
  - 起動直後にプロセス優先度を "high" に設定することで監視・実行タスクの優先度を高める。
  - DB 接続（SQLite / DuckDB）を確立し、後処理で確実に close() するように構成。
- Paper Trading の分離
  - paper_trading モードでは専用 SQLite（デフォルト data/paper_trading.db）に記録され、本番データと完全に分離される設計。
  - PAPER_FILL_MODE の入力値検証（instant/partial/never/reject）。

Fixed
- 安全性と堅牢性の改善
  - run_monitoring のポーリングで check_once() が例外を投げてもループを継続するよう例外ハンドリングを追加（ログ出力後に次ポーリングへ）。
  - run_execution は停止フラグ検出時に Engine.stop() を呼び出してスレッドを安全に終了させる。
  - validate_config の YAML 検証は PyYAML が未インストールの場合にスキップして警告を出す（起動時に致命的にならない）。
  - paper_verification_report: テーブルや列が存在しない場合に sqlite3.OperationalError を捕捉して適切にデフォルト値を扱う。
  - process_priority / set_cpu_affinity は権限不足・未対応 API に対して警告を出して処理をスキップし、クラッシュを防止。
  - .env 書き出しテンプレートにセクション区切り・注意書きを入れて誤ってコミットしないよう注意喚起。

Security
- config_setup にて生成される .env ファイルのヘッダに「.env は絶対に Git にコミットしないこと」という注意を追加。

Removed
- なし

Deprecated
- なし

Notes（実装上の注記・TODO）
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメント。将来的に前日終値や取得原価でのフォールバックを検討。
- risk_adjustment.calc_regime_multiplier:
  - 未知レジームは 1.0 でフォールバックし、警告を出す設計。
- research/factor_research.py は計算ロジックの実装が途中（ファイル末尾が途中で切れている）ため、完全なファクター計算実装は今後の追加作業が必要。

開発者向けメモ
- 自動ロードの順序: OS 環境 > .env.local (上書き) > .env (未設定のみ)
- .env の自動ロードをテストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL は正の整数を渡してください。0 以下または不正な値はデフォルト 60 秒にフォールバックします。

――――――
（以上）