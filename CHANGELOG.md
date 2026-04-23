# Changelog

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- （次回リリースに向けた変更をここに記載します）

## [0.1.0] - 初回リリース
公開初版。日本株自動売買システム「KabuSys」の基本的なコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージメタ: `src/kabusys/__init__.py` に __version__ = "0.1.0" を設定。

- 環境設定 / 設定読み込み
  - Settings クラス (`src/kabusys/config.py`) による環境変数ベースの設定管理を追加。
    - J-Quants、kabu API、LINE、DB パス、監視閾値、Kill Switch 等をプロパティ経由で取得。
    - KABUSYS_ENV, LOG_LEVEL の妥当性検証、PAPER_FILL_MODE の妥当性チェックを実装。
    - .env / .env.local の自動ロード機能（OS 環境変数を保護して読み込み順を制御）。
    - .env の行パース機能はシングル/ダブルクォート、エスケープ、コメント処理に対応。

- 環境設定ウィザード CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで .env を作成／更新するツールを実装。
    - シークレット入力のマスク、選択肢・デフォルト表示、既存値の再利用、キャンセルハンドリングをサポート。
    - .env 書き込みテンプレートを提供（コメント付き・Git にコミットしないよう警告）。

- 設定検証 CLI
  - `src/kabusys/validate_config.py`
    - .env と config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML パース検証（PyYAML があれば実行）、本番環境向け追加ガードを実装。
    - --strict オプションで警告を FAIL として扱う挙動をサポート。
    - 実行結果を INFO / WARNING / ERROR に分類して表示し、exit code を制御。

- 実行エントリとプロセス管理
  - `src/kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、PID ファイル管理、stop フラグ検知、paper_trading 時の専用 SQLite 利用（本番 DB と分離）を実装。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可。監視は常に本番 sqlite_path を使用。

- 発注エンジン本体（Execution）
  - `src/kabusys/execution/execution_engine.py`
    - Signal Queue Pull 型の発注エンジンを実装。
    - シグナル処理ウィンドウ（デフォルト 8:50–9:10）、WebSocket push ドレイン（9:10–15:30）等のセッション制御。
    - Gate 1（シグナルレベル）、Gate 2（実行レベル・レート制限）および Gate 3（ドローダウン監視）を実装。失敗時は kill_switch を発動。
    - kill_switch による全 active 注文のキャンセル処理、PID ファイルの管理、WebSocket スレッド起動/停止。
    - position_entries への約定記録（DuckDB 利用）と監視 DB へのトレードイベントログ機能（存在する場合）。

- 注文管理 / 状態機械
  - `src/kabusys/execution/order_record.py`
    - OrderState 列挙、OrderRecord データモデルと状態遷移検証ロジックを実装。
    - 許容される状態遷移テーブルと不正遷移時の InvalidStateTransitionError を提供。
    - 状態遷移時に関連フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）と updated_at を自動更新。
  - `src/kabusys/execution/order_manager.py`
    - OrderManager により signal_queue から受け取ったシグナルを OrderRecord と OrderRepository を通じて発注・同期・取消。
    - DuplicateOrder の防止（signal_id ベースの重複チェックと DB 部分ユニークインデックスの変換処理）。
    - send_order における耐障害設計（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted 等）によるクラッシュ後の復旧容易化。
    - OrderSentPendingError の扱い、sync_order による broker 状態同期、キャンセル処理のガード。

- ブローカークライアント（kabu station）
  - `src/kabusys/execution/kabu_client.py`
    - KabuStationClient を実装（同期 httpx ベース）。
    - トークンの遅延取得・自動再取得、401 時のリトライ処理、429（レート制限）や 5xx を BrokerAPIError / RateLimitError に変換。
    - kabu ステータスコード → 内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") マッピングを実装。
    - WebSocket push 受信用の stream_push の呼び出しを想定した設計（存在しない場合はスキップ）。

- 監視 DB 初期化
  - `src/kabusys/monitoring/monitoring_db.py`（参照箇所実装を想定）を run_monitoring/run_execution から呼び出し、監視用テーブルの初期化を保証する仕組みを追加。

- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`, `src/kabusys/utils/process_priority.py` を利用してログ設定とプロセス優先度設定を行うフローを各起動スクリプトに統合。

### 変更 (Changed)
- 本リリースは初版のため、既存からの「変更」はありません（新規実装）。

### 修正 (Fixed)
- 本リリースは初版のため、既存バグ修正はありません。

### 破壊的変更 (Removed / Deprecated)
- なし

### セキュリティ (Security)
- 機密情報（API トークン等）は .env に保存する設計とし、config_setup に「.env は絶対に Git にコミットしないこと」旨の注意を追加。
- Settings._load_env_file は OS 環境変数（プロセス外からの値）を保護する設計（protected set）になっており、意図しない上書きを防止。

## 既知の制約 / 注意事項
- YAML の内容検証は PyYAML がインストールされている場合にのみ実行されます。未インストール時は警告が出てパース検証をスキップします。
- KabuStationClient は同期版（httpx.Client）です。将来的に async に切り替える設計を見越した構造になっています。
- ExecutionEngine のセッションタイミングや DB 書き込み周りは本番実行前に十分なテストを推奨します（特に kill_switch / レコンシリエーション周り）。

---

今後のリリースでは以下を想定しています（例）:
- 非同期 HTTP クライアント対応（async/await）
- テスト・モックの充実化（Broker API のユニットテスト容易化）
- リスク管理設定の外部化（YAML/DB 化）および監視アラート強化

ご要望や不具合報告があれば issue をお寄せください。