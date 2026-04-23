# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
日付は本リリース作成日です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の改善
- Fixed: バグ修正
- Security: セキュリティ関連の注意事項

## [Unreleased]
- 

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能群を追加。
- 環境設定・読み込み
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git / pyproject.toml を探索して判定）。
    - .env のパースロジックを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを追加し、アプリケーション設定（J-Quants トークン、kabu API パスワード、DB パス、各種閾値、環境判定プロパティ等）をプロパティ経由で提供。
    - PAPER_FILL_MODE、paper_trading 用 sqlite パス、kill-flag 関連や閾値（CPU/MEM/DISK）などの設定取得を実装。無効な値は明示的に例外を送出。
- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する機能を追加。
    - 秘匿項目はマスク表示。選択肢・デフォルト値・説明付き。
    - .env の読み取り・書き込みロジック実装（既存値を保持して更新）。
    - 保存前に設定内容の確認プロンプトを行う。
    - .env ファイルに保存するテンプレートと注意書きを出力（.env を Git にコミットしないよう注意）。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ値（末尾が "_here" または "your_value"）を警告として検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、live 環境での追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - DUCKDB/SQLite のパス親ディレクトリ存在チェック（存在しない場合は警告）。
    - PyYAML がインストールされている場合は config/*.yaml のパース検証を実行。未インストール時はスキップして警告。
    - --strict オプションで警告も FAIL（exit code 1）として扱うモードを提供。
- 実行用スクリプト（エントリポイント）
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するランチャーを追加。プロセス優先度設定、ログ設定、DB 接続、pid/stop フラグ管理、スレッド起動/監視を実装。
    - paper_trading 環境時は paper_trading 専用 SQLite DB を使用して本番 DB と分離する挙動をサポート。
  - src/kabusys/run_monitoring.py
    - SystemMonitor をポーリング起動するランチャーを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
- 実行エンジン本体 / 実装
  - src/kabusys/execution/execution_engine.py
    - Signal Queue 方式の発注エンジンを実装。
    - シグナル処理フェーズ（例: 8:50–9:10）と WebSocket ドレインフェーズ（例: 9:10–15:30）をサポート。
    - Gate1（シグナルレベル）/ Gate2（エグゼキューションレベル、レート制限・サーキットブレーカ）/ Gate3（ドローダウン監視）の設計を実装し、NG の場合は kill_switch を発動。
    - サインループでの size_multiplier 適用（BUY のみ）、重複注文検出、発注遅延計測、発注結果の監視 DB ログ化を実装。
    - WebSocket push を受信して同期（sync_order）処理を行うワーカースレッドを実装（broker が stream_push を提供する場合）。
    - 起動時にリコンシリエーションを実行可能（Reconciler を注入）。
    - kill.flag の存在確認と KILL_FLAG_CLEAR_ON_START に基づく自動クリアのサポート。
    - PID ファイルの書き込みと起動終了時の削除処理を実装。
- 注文管理・状態遷移
  - src/kabusys/execution/order_record.py
    - OrderState 列挙と状態遷移ルールを実装（許容遷移マップ）。
    - OrderRecord データクラスを導入し、transition_to() による状態検証と更新を提供。無効な遷移は InvalidStateTransitionError を送出。
  - src/kabusys/execution/order_manager.py
    - OrderRecord と OrderRepository を組み合わせた外向け API を実装（create_order, send_order, sync_order, cancel_order）。
    - create_order で signal_id の重複アクティブ注文を検出して DuplicateOrderError を返す（DB の部分ユニーク制約も変換）。
    - send_order はクラッシュ耐性を考慮した 2 段階永続化（OrderSent を永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）を実装。
    - OrderSentPendingError を考慮し、pending 状態を DB に保存して呼び出し元へ再スロー。
    - sync_order は broker 側の状態を取得してローカル状態へ反映（部分約定の進行に合わせたフィールド更新を含む）。
    - cancel_order は終端状態ではキャンセル不可とし、実際に broker API を呼ぶ場合は broker_order_id を用いる。
- broker/kabu クライアント
  - src/kabusys/execution/kabu_client.py
    - kabu station REST API クライアント実装（httpx 同期クライアント）。
    - トークン取得、401 時の自動再取得とリトライ、429（レート制限）や 5xx のエラー分類、JSON パース失敗の明示的なエラー変換を実装。
    - websocket（push）サポートのためのインターフェースを想定（stream_push を持つ場合に WebSocket ワーカーで利用）。

### Changed
- 設定読み込みの堅牢化
  - .env のパースを強化し、様々な実ファイルに対して正しくコメント/クォート/エスケープを扱えるように改善。
- 起動時の安全性向上
  - ExecutionEngine / run_execution / run_monitoring においてプロセス優先度設定を導入し、DB 接続終了・pid ファイルクリーンアップ等のリソース管理を明確化。
- 監視（monitoring）に関する挙動
  - run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を利用する仕様を明確に実装。

### Fixed
- .env 読み込みエラー時に警告を出すように変更（ファイル読み取り失敗で例外を投げずに継続）。
- validate_config の YAML 検証は PyYAML がない場合に安全にスキップして警告するように修正。

### Security
- config_setup が生成する .env ヘッダに「.env は絶対に Git にコミットしないこと」を明記（秘密情報流出防止の注意喚起）。
- Settings._require の未設定時メッセージを改善し、.env.example を参照する旨を案内。

---

備考:
- 本バージョンはコードベースから推測して作成した初期リリース向けの CHANGELOG です。実際のコミット履歴が存在する場合は、それに合わせて日付・変更内容を調整してください。