KEEP A CHANGELOG
すべての変更はこのファイルに記録します。
フォーマットは https://keepachangelog.com/ja/ に準拠します。

[Unreleased]

[0.1.0] - 2026-04-22
Added
- 初回リリース（基本機能の実装）
- 環境設定管理
  - .env ファイルの自動読み込み機構を実装（OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）および高度なパーサ実装（export 形式、クォート内のバックスラッシュエスケープ、インラインコメント取り扱い）を追加（src/kabusys/config.py）。
  - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill フラグ、閾値、環境/ログレベル等）。（src/kabusys/config.py）
- .env 対話式ウィザード
  - 対話式 CLI による .env の初期作成・更新ウィザードを追加（デフォルト値、選択肢、シークレット表示マスク）。保存/確認フローを提供（src/kabusys/config_setup.py）。
- 設定検証ツール
  - .env と config/*.yaml を起動前に検査する CLI を追加。必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在確認、YAML パース（PyYAML があれば）などを行う（--strict オプションで警告を FAIL 扱いにできる）（src/kabusys/validate_config.py）。
- 実行エンジン / 監視
  - ExecutionEngine の初期実装（シグナル処理ループ、WebSocket push ドレイン、kill スイッチ、PID ファイル管理、セッションタイミング制御）を追加（src/kabusys/execution/execution_engine.py）。
  - 実行系起動スクリプトを追加（run_execution）。paper_trading 時の専用 SQLite 分離、プロセス優先度設定、stop フラグ検知等を含む（src/kabusys/run_execution.py）。
  - SystemMonitor 用のポーリングループ起動スクリプトを追加（run_monitoring）。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）、監視 DB 初期化を行う（src/kabusys/run_monitoring.py）。
- 発注関連
  - OrderRecord（状態遷移ロジックを持つ純粋モデル）を実装。許可される状態遷移の定義と不正遷移時の例外を提供（src/kabusys/execution/order_record.py）。
  - OrderManager を実装し、signal_queue→DB→broker API の発注フロー（create/send/sync/cancel）を提供。DuplicateOrder 判定、2相永続化パターン（OrderSent 前後の扱い）、OrderSentPendingError の取り扱い、sync による状態復元（reconciliation を想定）を実装（src/kabusys/execution/order_manager.py）。
  - Broker クライアント抽象と kabu station 実装（KabuStationClient）を追加。トークン管理、自動再取得、HTTP エラー・429/500 系の変換、WebSocket push の受信フックをサポート（src/kabusys/execution/kabu_client.py）。
- リスク／リコンシリエーション／監視統合の点検
  - ExecutionEngine 内での Gate ベースのリスクチェック（Gate1: シグナル単位、Gate2: 実行レート制御・サーキットブレーカー、Gate3: ポートフォリオ指標監視）を実装。Gate3 NG 時は kill_switch 発動。発注後の position_entries 更新、監視 DB へのトレードイベント記録処理を組み込み（src/kabusys/execution/execution_engine.py）。
- DB 周り
  - DuckDB（分析用）と SQLite（監視/注文履歴）を併用する実装を導入。paper_trading では SQLite を分離して本番 DB と混ぜない設計（src/kabusys/run_execution.py、src/kabusys/run_monitoring.py、src/kabusys/config.py）。

Changed
- n/a（初回リリースのため履歴なし）

Fixed
- n/a（初回リリースのため履歴なし）

Removed
- n/a

Security
- 環境変数（シークレット）表示は対話ウィザード等でマスクし、.env を Git にコミットしない旨の注意を出力（src/kabusys/config_setup.py）。

Notes / 使用方法
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict
- 実行:
  - 実行エンジン: python -m kabusys.run_execution
  - 監視プロセス: python -m kabusys.run_monitoring

開発者向け補足
- プロジェクトバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"（初期リリース）。
- 設定の自動読み込みはプロジェクトルートの検出に依存（.git または pyproject.toml を基準）。配布後やテスト時に自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

-----