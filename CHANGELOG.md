# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
このファイルはコードベースから推測して作成したもので、実装上の主な機能・振る舞い・改善点をまとめています。

## [0.1.0] - 2026-04-22

### Added
- プロジェクト初期リリース相当の基本機能を追加。
- 環境変数/設定管理
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得する API を提供。
  - 必須/オプションの環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、デフォルト値、型変換（float/Path/bool）をサポート。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）と paper_trading 用 SQLite パスのサポート。
  - settings グローバルインスタンスを提供。
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を起点）を探索して .env / .env.local を自動読み込み（OS 環境変数を保護）。
  - .env のパースロジックは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢な実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。
- 対話式設定ウィザード
  - python -m kabusys.config_setup による .env の対話式作成/更新機能を追加。
  - 各設定項目の説明、選択肢、シークレット入力（表示マスク）を提供。生成される .env のテンプレートを整備。
- 設定検証 CLI
  - python -m kabusys.validate_config を追加。環境変数（必須/プレースホルダ検出）、KABUSYS_ENV/LOG_LEVEL の値、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
  - --strict オプションで警告を失敗扱い（exit 1）にできる。
  - 出力は INFO/WARNING/ERROR を整形して表示し、適切な終了コードを返す。
- 実行/監視起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。paper_trading 時は専用 DB を使い、本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。監視は常に本番 sqlite_path を使用。
  - いずれもプロセス優先度を「high」に設定するユーティリティ呼び出しを行う（set_process_priority）。
  - PID / 停止フラグ（stop_requested.flag, kill.flag）管理を実装。
- Execution エンジン本体
  - ExecutionEngine を実装。シグナル読み込み（DuckDB）、Gate1/2/3 によるリスクチェック、発注フロー、WebSocket push ドレイン、kill_switch 発動ロジックを提供。
  - セッションスケジュール（signal_send_start/end、market_close）に基づく処理フローを実装。
  - 発注成功/保留/失敗に対するロギングと監視DBへのイベント記録フックを追加。
  - 発注時の position_entries 更新（BUY/SELL の扱い）を実装（DuckDB へ書き込み）。
- 注文関連コンポーネント
  - OrderRecord: 注文状態（OrderState）を列挙し、状態遷移検証（Allowed transitions）を行う純粋ビジネスロジックのデータモデルを追加。InvalidStateTransitionError を導入。
  - OrderManager: signal_id 重複検出（DuplicateOrderError）、create/send/sync/cancel の高レベル API を実装。
    - send_order はクラッシュ耐性を考慮した二相的永続化（OrderSent を先に永続化→ broker 呼び出し→ broker_order_id を永続化→ OrderAccepted に遷移）を行う設計。
    - OrderRejectedError, OrderSentPendingError の扱いを明確化。OrderSentPendingError は broker_order_id を保存した上で再スロー。
    - sync_order は broker 側ステータスを内部 OrderState にマッピングし、部分約定の進展を反映する更新ロジックを提供。
    - cancel_order はキャンセル不可能状態のガードを実装し、必要に応じて broker API を呼び出して Cancelled に遷移。
- ブローカー実装（kabu station）
  - KabuStationClient を追加（httpx 同期クライアント）。
  - トークン管理（遅延取得と 401 時の再取得）、HTTP エラー/タイムアウト/ネットワークエラーを BrokerAPIError に変換。
  - 429 を RateLimitError として扱い、ステータスコードに基づく例外分岐を実装。
  - kabu station の状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマッピング。
- DB/監視関連
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）への参照と利用場所を追加（監視/実行両方で利用）。
  - run_monitoring/run_execution で sqlite3 / duckdb の接続管理を行い、終了時にクローズするように実装。

### Changed
- なし（初回リリース想定）。コード内に多くの堅牢化・安全設計（クラッシュ耐性、入力パース、検証）が施されていることを反映。

### Fixed
- なし（初回リリース想定）。

### Security
- 環境変数を直接コード上にコミットしないよう .env に関する注意書きを config_setup の出力に記載。
- .env の自動ロードでは OS 環境変数を保護する仕組みを導入（protected set）。

### Notes / Implementation details（補足）
- .env パーサは export プレフィックス、クォート内のエスケープ、インラインコメントの取り扱い等、実運用で発生しやすいケースに対応しています。
- validate_config は PyYAML が未インストールの場合、YAML 内容検証をスキップして警告を表示します（存在チェックは継続）。
- ExecutionEngine の kill_switch は全 active 注文をキャンセルするためのフェイルセーフとして設計されています。キャンセル時に BrokerAPIError が発生しても処理は継続します。
- OrderManager.create_order は内部的に SQLite の部分ユニークインデックス（orders.signal_id）違反を DuplicateOrderError に変換して扱う実装があります。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用することが明示されています（監視は本番データを想定）。

---

（この CHANGELOG はコードを静的に解析して推測した内容に基づいて作成しています。実際のリリースノート作成時はコミットログ・PR の内容に基づいて更新してください。）