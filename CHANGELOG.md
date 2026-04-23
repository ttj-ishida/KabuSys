Keep a Changelog
=================

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の書式に準拠しています。

フォーマット
- 変更は「Added / Changed / Fixed / Removed / Security」などのカテゴリで記載します。
- 各バージョンごとに日付を付与します。

0.1.0 - 2026-04-23
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装。
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（OS 環境変数を保護し、.env / .env.local の順に読み込み）。環境変数のパースは export 形式やクォート・コメントに対応（src/kabusys/config.py）。
  - Settings クラスを提供し、アプリケーション全体で環境設定を型付きで取得可能（J-Quants / kabu API / DB パス / 各種閾値など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
- 設定ウィザード
  - 対話式 .env 作成・更新ツールを実装（src/kabusys/config_setup.py）。
  - デフォルト値、選択肢、シークレット表示、既存 .env 読み込み、保存確認、および書式化された .env 出力をサポート。
- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml を検証する CLI を実装（src/kabusys/validate_config.py）。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML があれば内容検証）、live 環境向けの追加ガードを提供。
  - --strict オプションで警告も FAIL 扱いにできる。
- 実行スクリプト
  - ExecutionEngine を起動する run_execution スクリプトを実装（src/kabusys/run_execution.py）。paper_trading 時は専用 SQLite（paper_trading.db）を使用し、本番 DB と分離。
  - SystemMonitor を起動する run_monitoring スクリプトを実装（src/kabusys/run_monitoring.py）。MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応、監視は環境に関わらず本番 sqlite_path を使用。
- 発注エンジン
  - ExecutionEngine：シグナルの読み込み、Gate 検査（3段階）、WebSocket ドレインループ、セッション制御（発注時間帯・終了処理）を実装（src/kabusys/execution/execution_engine.py）。
  - ポジションエントリ管理（DuckDB への書き込み）と発注遅延／Pending の取り扱いを実装。
  - kill.flag の検査と KILL_FLAG_CLEAR_ON_START 動作による起動振る舞いを実装。PID ファイル管理。
- 注文管理（Order State Machine）
  - OrderRecord：状態遷移ロジックとデータモデル（純粋ロジック、DB非依存）。許容遷移を厳密に定義し、不正遷移時に例外を送出（src/kabusys/execution/order_record.py）。
  - OrderManager：OrderRecord と OrderRepository を組み合わせた外向け API を実装（発注作成・送信・同期・キャンセル）。クラッシュ安全性を考慮した 2 相永続化（OrderSent 前後の処理）や Reconciliation を想定した振る舞いを実装（src/kabusys/execution/order_manager.py）。
  - DuplicateOrder チェック（signal_id 単位）と DB のユニーク制約に基づく検出。
- Broker/Kabu クライアント
  - KabuStationClient：kabuステーション REST API の同期クライアントを実装。httpx を利用し、トークン取得・自動再取得、401 リトライ、429（RateLimit）/5xx のエラー分類、JSON パース失敗の例外変換を実装（src/kabusys/execution/kabu_client.py）。
  - WebSocket push（stream_push）がある場合の受信スレッド連携（ExecutionEngine 側）を想定。
- リスク管理・調整
  - RiskManager（利用箇所あり）との連携を想定した API 呼び出しを実装（レート制限・サーキットブレーカー検知など）。
  - Reconciler（利用箇所あり）を用いた起動時のリコンシリエーション処理を ExecutionEngine に統合。
- 監視 (Monitoring)
  - monitoring アプリケーション向けの DB 初期化呼び出しとポーリングループ、監視イベントの記録呼び出し箇所を実装。
- ユーティリティ
  - プロセス優先度設定（set_process_priority）とロギング初期化（setup_logging）を起動時に使用する設計で統合。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。

Changed
- （初回リリースのため特になし）

Fixed
- （初回リリースのため特になし）

Notes / 実装上の要点
- .env のパースはシングル/ダブルクォート内のエスケープや、非クォート時のインラインコメント扱いに対応しているため、複雑な .env の記述も正しく解析されることを意図しています。
- OrderManager.send_order はクラッシュ耐性を高めるため、OrderSent 状態を DB にコミットしてから外部 API 呼び出しを行い、その後 broker_order_id を先に永続化してから OrderAccepted へ遷移することで Reconciliation を助ける設計になっています。
- ExecutionEngine はセッションタイミング（signal_send_start / signal_send_end / market_close）に沿ってシグナル処理と push ドレインを行い、kill_switch による即時停止と active 注文の取り消しをサポートします。
- KabuStationClient は同期 HTTP クライアントとして実装されているが、将来的に async 版（httpx.AsyncClient）へ差し替え可能な設計になっています。
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行います。PyYAML 未導入時は警告表示でスキップします。

Known issues / 今後の改善予定
- 一部の依存モジュール（OrderRepository / BrokerClientFactory / Reconciler / RiskManager 実体など）は本差分に含まれていないため、統合テスト・エンドツーエンド検証が必要です。
- KabuStationClient の WebSocket 周りは外部ライブラリ（websocket 等）に依存しており、実運用での接続安定性や再接続戦略の強化が今後の課題です。
- エラーハンドリングおよび監視の粒度をさらに細かくし、アラート連携（LINE 等）を強化する予定です。

License
- 各ソースファイルのライセンス表記に従ってください（本CHANGELOG自体は簡易的なリリースノートです）。

--- 
（このCHANGELOGは、提供されたソースコードから推測して作成しました。実際のリリースノートはリリース手順・バージョン管理履歴に基づき調整してください。）