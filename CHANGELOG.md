CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内のコード状態から推測して作成しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 基本的な自動売買システム「KabuSys」を実装。
  - パッケージバージョンを __version__ = "0.1.0" として公開。
- 設定関連
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得する機能を実装（src/kabusys/config.py）。
    - J-Quants / kabuステーション API トークンや DB パス、LINE 通知設定、監視閾値などをプロパティで取得。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実施し、無効な値は ValueError を送出。
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出に .git または pyproject.toml を使用）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env 解析ロジックを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどをサポート。
    - 環境変数読み込み時に既存の OS 環境変数を保護するための protected セットをサポート。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話的に .env を生成/更新する run_wizard / main を提供。
    - シークレット項目は表示をマスク、デフォルト値・選択肢をサポート。
    - .env 書き込みテンプレートを用意（Git へのコミット禁止の注意書き等を含む）。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - .env と config/*.yaml の存在/妥当性を起動前に検査。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、PyYAML の有無を考慮した YAML パースチェックを実装。
  - --strict フラグで警告も FAIL 扱いにできる。
- 実行エントリ / デーモン系スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - ExecutionEngine を起動する main を提供。プロセス優先度設定や DB 接続、pid/stop フラグ処理を実施。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する実装。
- Execution 系コア
  - ExecutionEngine の実装（src/kabusys/execution/execution_engine.py）。
    - シグナルの読み取り（DuckDB）、Gate1/2（シグナル・実行レベルのリスク検査）、発注処理、WebSocket push のドレイン、Gate3（ドローダウン監視）を備えたセッション制御。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START による起動時の挙動を実装。
    - PID ファイルの書き込み・削除を実装。
    - 発注成功/保留/失敗時に監視DBへのログ記録を試みるフックを提供（monitoring_db が注入されている場合）。
  - OrderManager / OrderRecord / OrderRepository 周りのロジック
    - OrderRecord（状態遷移を検証する純粋なビジネスロジック）を実装（src/kabusys/execution/order_record.py）。
      - 明示的な OrderState 列挙、許可遷移表、transition_to による検証と更新。
      - 不正遷移時に InvalidStateTransitionError を raise。
    - OrderManager を実装（src/kabusys/execution/order_manager.py）。
      - create_order: signal_id の重複チェック（DB の部分ユニークインデックス違反は DuplicateOrderError に変換）。
      - send_order: クラッシュ耐性を考慮した 2 段階永続化フロー（OrderSent を先にコミット→broker 呼び出し→broker_order_id を保存→OrderAccepted へ遷移等）。
      - OrderSentPendingError を特別扱い（broker_order_id を保存して OrderSent のまま残し、例外を伝播）。
      - sync_order: broker 側の状態を照合して状態/約定数量等を同期。OrderSent→Filled のような直接遷移を取り扱うため OrderAccepted を経由させる処理あり。
      - cancel_order: 終端状態のキャンセル不可判定、broker への cancel 呼び出し、Cancelled への遷移。
  - Broker クライアント
    - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
      - httpx を用いた同期 REST クライアント。トークン取得、401 時の再取得とリトライ、429（RateLimit）・5xx のエラー判定、JSON パース例外の変換を実装。
      - kabu ステーション注文状態コードを内部ステータスにマッピング。
      - stream_push（WebSocket）を用いた push 受信を想定した実装スケルトンを含む（WebSocket 関連の利用をサポート）。
- 監視 / DB
  - monitoring_db の init_monitoring_db を呼び出す箇所を run_monitoring / run_execution で実行し、監視用テーブルの作成を保証するように変更。
- その他ユーティリティの想定連携
  - setup_logging, set_process_priority 等のユーティリティを呼び出し、アプリケーションの起動時にログ設定・プロセス優先度設定を行うように統合。

Changed
- 新規リリースのためのコード統合。各コンポーネントはモジュール分割され、実行スクリプトから組み立てられる構成になった。

Fixed
- .env 解析の堅牢性を向上（引用符内のエスケープ、export プレフィックス、コメント取り扱い）して、環境変数の誤解釈を減らすよう改善。

Security
- .env の取り扱いに関して、config_setup にて「.env は絶対に Git にコミットしないこと」と明記。

Notes / Migration / Breaking Changes
- Settings は起動時に自動で .env を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。自動ロードの振る舞いに依存する既存スクリプトは注意してください。
- Settings のプロパティは不正値に対して ValueError を送出します。既存のコードは例外処理を加える必要がある場合があります（特に KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）。
- validate_config の --strict を使用すると警告も失敗として exit(1) になります。CI 等で厳密チェックする場合は --strict を使用してください。
- ExecutionEngine は PID / kill.flag に依存します。kill.flag の存在により起動が拒否される場合があるため運用手順に注意してください。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存の kill.flag をクリアして起動します（本番では推奨されません）。

開発者向け補足
- YAML の内容検証は PyYAML がインストールされている場合にのみ実行されます。PyYAML がない環境ではファイル存在チェックのみ行い、パースチェックはスキップされます。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対してフォールバックする堅牢な実装（0 以下または非数値はデフォルト 60 秒に戻る）を行います。
- OrderManager の send_order はクラッシュやネットワーク障害に耐えるための設計（OrderSent の永続化、broker_order_id の先行保存、OrderSentPendingError の特別扱い）を採用しています。リコンシリエーション機能（Reconciler）と組み合わせることでクラッシュ後の状態回復を想定しています。

上記はソースコードから推測して作成した変更履歴です。必要に応じて具体的なチケット番号、詳細な実装コメントや既知の制限事項を追加してください。