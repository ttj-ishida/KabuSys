CHANGELOG
=========
すべての注目すべき変更を記録します。
このファイルは Keep a Changelog の形式に準拠しています。
（注: 以下の変更点は提示されたコードベースの内容から推測した要約です）

Unreleased
----------
- (現時点での未リリースの変更はありません)

0.1.0 - 2026-04-22
-----------------
Added
- 起動前に環境変数や設定ファイルの不備を検出する CLI を追加。
  - python -m kabusys.validate_config により .env と config/*.yaml の検証が可能。
  - --strict オプションで警告を失敗扱いにできる。
  - PyYAML 未インストール時は YAML 検証をスキップし、警告を出力する挙動を実装。
- 対話式環境設定ウィザードを追加。
  - python -m kabusys.config_setup により .env ファイルを対話的に作成/更新可能。
  - デフォルト値、選択肢、シークレット入力等の項目定義を含む。
  - 既存 .env の読み込み・確認・保存処理を実装。
- 環境変数/設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルート自動検出 (.git / pyproject.toml を探索) に基づく .env 自動読み込み（.env, .env.local の優先度対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env のパースはクォート／エスケープ／インラインコメントに対応。
  - protected（OS 環境変数）を尊重した上書き挙動を実装。
  - Settings クラスで各種設定値を型付きで提供（DB パス、LINE トークン、KABUSYS_ENV, LOG_LEVEL など）。
  - PAPER_FILL_MODE の妥当性チェックや paper_trading 用 SQLite パスの分離を実装。
- 実行エントリスクリプトを追加:
  - run_execution: ExecutionEngine の起動スクリプト（プロセス優先度設定、PID/停止フラグ管理、DB 接続、スレッド管理）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔上書き可能、監視 DB 初期化）。
- 発注関連コアコンポーネントを実装:
  - OrderRecord: 注文状態遷移を表すデータモデルと遷移検証（OrderState enum と InvalidStateTransitionError）。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API（作成・送信・同期・キャンセル）。
    - send_order 実行時に OrderSent を永続化してから broker API を呼び、broker_order_id の先コミット → OrderAccepted へ遷移する 2 相永続化パターンを採用（クラッシュ耐性向上）。
    - OrderSentPendingError（注文が番号を発行するが約定しないケース）を扱い、pending 状態を DB に残す挙動を実装。
    - DuplicateOrderError による同一 signal_id の重複防止。
  - ExecutionEngine: シグナル読み込み・Gate（Gate1: シグナルレベル、Gate2: エグゼキューションレベル、Gate3: ドローダウン監視）を備えた発注エンジン。
    - シグナル処理ループ（発注開始/締切/市場クローズの時間管理）、WebSocket push ドレイン、kill_switch（全 active 注文のキャンセル）等を実装。
    - 発注成功/保留/失敗時の監視 DB への記録（監視 DB が提供されている場合）や position_entries への書き込みロジックを追加。
    - paper_trading 環境では paper 用 SQLite を使用して本番 DB と分離。
- broker クライアント（KabuStationClient）を実装:
  - httpx を用いた同期 REST 実装。トークン取得（遅延初期化）と 401 時のトークン自動再取得とリトライを実装。
  - レスポンス JSON パース失敗やタイムアウト／ネットワークエラーを BrokerAPIError に変換。
  - 429 応答に対する RateLimitError の判定、サーバーエラー時の取り扱いを実装（エラーハンドリングの基盤）。
  - WebSocket push 受信のための stream_push フックに対応（存在しない場合はスキップ）。
- 監視周り（monitoring）関連:
  - monitoring DB の初期化関数（init_monitoring_db）呼び出しを run_monitoring/run_execution で行う。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する旨の設計。

Changed
- ログ・起動周りの共通改善:
  - プロセス優先度をセットするユーティリティ呼び出しを導入（高優先度での実行を想定）。
  - PID ファイルの書き出し / 削除処理を追加。
  - kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START による自動クリア挙動を実装（起動防止/強制クリアの選択肢を提供）。
- 設定検証ロジックの細分化:
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック（自動作成される旨の警告）等を実装。
  - config/*.yaml の存在確認と（PyYAML があれば）パース検証を行う。

Fixed
- 注文状態遷移の不整合に対する保護:
  - OrderRecord.transition_to で不正遷移を InvalidStateTransitionError として明示的に検出するようにした。
  - sync_order 実行時に OrderSent → Filled/PartialFill へ直接遷移できない場合は一旦 OrderAccepted を経由して復元するリカバリロジックを実装（Reconciliation を意識した堅牢化）。
- DB/IO 安全性の向上:
  - send_order の実装で broker_order_id を先に永続化することで、クラッシュ後の照合（reconciliation）が可能になるようにした。
  - .env ファイル読み込み時の I/O エラー発生時に警告を出すようにした。

Security
- .env の取り扱いについて強調メッセージを config_setup の出力に追加:
  - .env を絶対に Git にコミットしない旨の注記を生成ファイル先頭に含める。

Notes / Implementation details
- 設計方針の一部:
  - ExecutionEngine はシグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）に分けた処理モデルを採用。
  - position_entries へのエントリは発注成功時に記録し、BUY は pending でも記録する設計（キャンセル時はリコンシリエーションで回収）。
  - Monitoring は環境に依らず本番 sqlite を用いる（監視データは常に共通 DB に保存する方針）。
- 自動検出/互換性:
  - .env の自動ロードはプロジェクトルートの検出に依存するため、配布後や CWD に依存しない挙動を考慮している。
  - .env のパースは export プレフィックス、クォート付き値、エスケープ、インラインコメント等に対応。

今後の改善候補（コードから推測）
- KabuStationClient の WebSocket 処理と HTTP クライアントの async 対応。
- より詳細な監視イベント・メトリクスの追加と外部監視連携。
- config/*.yaml のスキーマ検証（PyYAML に加えてスキーマバリデータ導入）。
- テスト支援のため KABUSYS_DISABLE_AUTO_ENV_LOAD のドキュメント化とユーティリティの拡充。

以上。