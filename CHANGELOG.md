# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはプロジェクトの主要機能・追加点・重要な挙動をコードベースから推測してまとめたものです。

文言は日本語で記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23
初回リリース。自動売買システム KabuSys のコア機能を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 環境変数/設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env パーサを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - _load_env_file による上書きロジック (override / protected) を実装し、OS 環境変数の保護をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。
  - Settings クラスを追加。アプリケーション設定をプロパティ経由で取得可能（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, KABUSYS_ENV/LOG_LEVEL の妥当性チェック等）。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
  - 環境/ログレベルの妥当性検査で不正値は ValueError を発生させる。

- 対話式設定ウィザード (src/kabusys/config_setup.py)
  - .env の初期作成・更新を支援する対話型ウィザードを実装（secret マスク表示、選択肢、説明表示）。
  - 既存 .env の読み込みと Enter による既存値再利用をサポート。
  - .env を所定フォーマットで出力する _write_env を実装し、生成時の注意コメントを埋め込む。
  - 使用例・CLI エントリポイントを提供: python -m kabusys.config_setup

- 設定検証 CLI (src/kabusys/validate_config.py)
  - 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
  - 必須環境変数チェック (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) とプレースホルダ検出（"_here" / "your_value"）を実装。
  - KABUSYS_ENV、LOG_LEVEL の妥当性チェック、live 環境時の追加注意喚起（LINE 設定や Kill Flag 設定の注意）を追加。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック（不足時は警告）を追加。
  - config/*.yaml の存在確認と PyYAML が利用可能な場合のパース検証を追加（PyYAML 未インストール時はパース検証をスキップして警告）。
  - --strict オプションで警告を FAIL（exit 1）扱いにできる。

- 実行系エントリスクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の起動フローを定義。プロセス優先度設定、PID/停止フラグ検査、DB 接続（paper_trading 時は paper_sqlite_path に分離）などを実装。
    - スレッドでエンジンを起動し、stop_requested.flag 検出で安全停止。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ stop_requested.flag の検出でループ終了。監視 DB（SQLite）は環境に関わらず本番 sqlite_path を使用する設計。

- Execution / 発注周りのコア実装
  - ExecutionEngine (src/kabusys/execution/execution_engine.py)
    - シグナル処理 → push ドレインのセッション制御（時間帯: デフォルトで 8:50-9:10 / ドレイン 9:10-15:30 / market_close 15:30）。
    - kill.flag による kill switch 挙動、PID ファイル書き込み、WebSocket push のドレイン機能、push からの同期と Gate 3（ドローダウン監視）を実装。
    - シグナル処理では Gate1（シグナルレベル）/ Gate2（実行レート制限）を適用し、発注は最大3回の rate-limit リトライを行う。
    - 発注後には position_entries（DuckDB）へ約定日登録の処理を行い、失敗しても発注フローは継続。
    - 発注メトリクス（レイテンシ等）を監視 DB に記録するフックを持つ（monitoring_db が渡された場合）。
  - OrderRecord（状態遷移モデル） (src/kabusys/execution/order_record.py)
    - 注文状態列挙 OrderState と許可される遷移表を定義し、不正遷移時に InvalidStateTransitionError を送出する純粋ドメインモデルを実装。
    - transition_to により state 更新および関連フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）と updated_at を安全に更新。
  - OrderManager（発注 API 層） (src/kabusys/execution/order_manager.py)
    - create_order: signal_id の重複チェック（DB/メモリ検査）、UUID による client_order_id 採番、DB への保存と DuplicateOrderError の定義/変換（部分ユニークインデックス違反の取り扱い）。
    - send_order: クラッシュ安全性を考慮した 2 段階永続化戦略を実装（OrderSent を DB にコミット → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError のハンドリングを実装。
    - sync_order: broker の状態照会に基づく同期処理を実装。broker が返すステータスに応じて部分約定更新や状態遷移を行う。
    - cancel_order: cancel 可否判定（特定終端状態では不可）と、broker API 呼び出し（必要な場合）後に Cancelled に遷移。
    - DuplicateOrderError、InvalidStateTransitionError の利用によりビジネスルールを明確化。

- Broker クライアント実装 (src/kabusys/execution/kabu_client.py)
  - KabuStationClient を実装（同期 httpx クライアント）。
  - トークン取得を遅延初期化し、401 応答時はトークン再取得して自動リトライする処理を実装。
  - レスポンス JSON パース失敗やネットワークエラーを BrokerAPIError に変換。
  - 429 は RateLimitError として扱う。サーバー 5xx は BrokerAPIError を発生。
  - kabu station の注文状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマッピングする定義を追加。
  - WebSocket push 用の stream_push 呼び出しを想定した設計（on_message コールバック登録）。

- リスク管理・再同期間合（Reconciliation）その他関連インターフェース
  - RiskManager、Reconciler、OrderRepository、BrokerAPIProtocol 等の利用を想定した各層の結合ポイントを実装（具体的な実装は別モジュールとして分離）。

### 変更 (Changed)
- （初版のため無し）

### 修正 (Fixed)
- （初版のため無し）

### 注意事項 / 既知の挙動
- validate_config の YAML パースは PyYAML がインストールされていない場合はスキップされ、警告が出るのみ。CI 等で厳密検査する場合は PyYAML を依存に追加してください。
- Settings による環境値の妥当性チェックは Property レベルで ValueError を投げます。呼び出し側で適切にハンドリングしてください。
- ExecutionEngine の時刻判定はローカル時刻を使用します（time()）。テストでは run_session の個別メソッドを直接呼ぶことが想定されています。
- .env は絶対にリポジトリへコミットしないでください（config_setup の出力ヘッダにも注意書きあり）。

### セキュリティ
- シークレット値（API トークンやパスワード）は対話ウィザードでマスク表示しますが、.env 内は平文保存になります。運用時は適切にファイル権限・配布管理を行ってください。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミットログ・PR の内容に基づいて調整してください。