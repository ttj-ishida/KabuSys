CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」準拠、セマンティックバージョニングを使用します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-23

最初の公開リリース。日本株自動売買システム KabuSys の基礎機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env ファイルおよび環境変数からの設定読み込みを自動で行う（プロジェクトルート検出ロジックあり）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須/任意設定のプロパティ群（J-Quants トークン、kabu API パスワード、DB パス、LINE トークンなど）。
    - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）。
    - paper_trading 用 DB パスを本番 DB と分離（PAPER_TRADING_SQLITE_PATH、paper_sqlite_path）。
- .env パーサ/ローダ
  - シンプルだが頑健な .env パーサ実装（クォート、エスケープ、コメント取り扱い、export 形式対応）。
  - OS 環境変数を保護して .env を読み込む挙動（override/protected の仕組み）。
- 対話式設定ウィザード CLI
  - src/kabusys/config_setup.py にウィザードを実装。
  - .env の初期作成・更新を対話的に支援。シークレット項目はマスク表示。
  - デフォルト値、選択肢、項目説明を備え、最終確認後に .env を書き出す。
- 設定検証 CLI
  - src/kabusys/validate_config.py に CLI を実装。
  - .env と config/*.yaml の存在・妥当性検証（PyYAML が未インストールの場合は YAML 検証をスキップして警告）。
  - 必須環境変数未設定の検出、プレースホルダ値検出（例: endswith "_here" や "your_value"）。
  - KABUSYS_ENV、LOG_LEVEL 等の妥当値チェック、DB パスの親ディレクトリ存在チェック、live 環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションで警告も失敗（exit 1）扱いにできる。
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度の設定、PID ファイル管理、stop フラグ検出、paper_trading時の DB 分離、duckdb 接続、監視 DB 初期化。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き、SQLite / DuckDB 接続、停止フラグ対応。
- 実行エンジンと発注ロジック
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（開始/終了時刻設定）、push ドレインループ、WebSocket push の受信（_push_queue 経由）、kill_switch の実装。
    - ポジション記録（position_entries への書き込み）、Gate1/2/3 のリスクチェック呼び出し、API レート制限ハンドリング（リトライ）。
    - Reconciliation 実行サポート（起動時）。
  - OrderRecord（状態マシン）を実装（src/kabusys/execution/order_record.py）。
    - 明示的な状態列挙（created/sent/accepted/partial/filled/closed/cancelled/rejected）と遷移制約、遷移時のタイムスタンプ更新、関連フィールド更新。
  - OrderManager 実装（src/kabusys/execution/order_manager.py）。
    - create/send/sync/cancel の外向け API。DuplicateOrder の検出、二相永続化（OrderSent 前後のクラッシュ安全設計）、OrderSentPendingError の取り扱い、broker 照合による同期。
- ブローカークライアント
  - KabuStationClient 実装（src/kabusys/execution/kabu_client.py）。
    - httpx を用いた同期 REST クライアント、トークン取得と自動再取得ロジック、HTTP エラー（401/429/>=500）を適切な例外へ変換。
    - websocket push のサポート（stream_push を持つ broker によるメッセージ取り込みに対応）。
    - kabu ステーションの状態コードを内部ステータスにマッピング。
- 監視関連
  - monitoring_db 初期化呼び出しを実装箇所に追加（monitoring 用 SQLite 初期化保証）。
  - ExecutionEngine から監視 DB へのトレードイベント記録（log_trade_event 呼び出し）に対応する箇所を用意。
- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティ呼び出しをスクリプトから利用（起動時に優先度を high に設定する仕組み）。

### 変更 (Changed)
- （このリリースは初版のため該当なし）

### 修正 (Fixed)
- （このリリースは初版のため該当なし）

### 既知の注意事項
- PyYAML が未インストールの場合、config/*.yaml の内容検証はスキップされ、警告が出ます（validate_config）。
- .env の自動読み込みはプロジェクトルート検出に依存します。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険（validate_config や run_* スクリプトで警告を出す）。
- 一部の外部依存（実際の kabuステーション アプリ、httpx、duckdb、sqlite3 等）が必要です。テストや CI ではこれらをモックしてください。

---

今後の予定（例）
- ブローカー API のエラーハンドリング強化・ユニットテスト追加
- ExecutionEngine の統合テスト拡充（時間依存ロジックのモック化）
- Monitoring/Alerts の拡張（LINE 通知のテンプレート化等）

参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/