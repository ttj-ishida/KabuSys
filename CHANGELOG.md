CHANGELOG
=========

すべての注目すべき変更は下記に記録します。
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-23
------------------

Added
- パッケージ初期リリース。
- 環境設定 / 管理
  - Settings クラスを提供。環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL 等）を取得する API を実装。
  - 自動 .env ロード機能を実装。プロジェクトルート（.git または pyproject.toml を探索）を起点に .env、.env.local を優先順に読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env 解析ロジックは引用符・エスケープ、コメント処理、export KEY=val 形式に対応。
  - Settings による型変換/検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の妥当性チェック、パスは Path に変換）。
- 対話式設定ウィザード
  - python -m kabusys.config_setup により .env を対話式で作成・更新する CLI を追加。デフォルト値、選択肢、シークレット入力（表示マスク）、既存値の再利用をサポート。
  - .env 保存時にテンプレートヘッダを出力し、Git へ .env をコミットしないよう注意を表示。
- 設定検証ツール
  - python -m kabusys.validate_config を追加。必須環境変数の存在確認、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース確認（PyYAML 未インストール時はスキップ）を実施。
  - --strict オプションにより警告を FAIL と扱い exit(1) を返すモードを実装。
  - 本番環境（KABUSYS_ENV=live）用の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値チェック）を実装。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。paper_trading 用に専用 SQLite を使う分離設計。プロセス優先度設定、PID ファイル、停止フラグ検出に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能。Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
- 発注エンジン / 注文管理
  - ExecutionEngine を実装。signal の読み出し（DuckDB）→ Gate1/Gate2 によるリスク判定 → 発注（OrderManager 経由）→ push ドレイン処理 のフローを実装。
  - シグナル処理時間帯（デフォルト 8:50–9:10）およびセッション終了時刻（デフォルト 15:30）を設定可能。
  - WebSocket（kabu push）を受けるワーカースレッド、push_queue による非同期処理を実装。
  - ExecutionEngine に kill_switch 機能を実装：全 active 注文のキャンセルと停止イベント発火。
  - 発注失敗・遅延時の監視 DB へのログ書き込みフックをサポート（監視 DB が渡された場合）。
- 注文モデルと状態遷移
  - OrderRecord と OrderState を実装。状態遷移の許可表（_ALLOWED_TRANSITIONS）を定義し、不正遷移で InvalidStateTransitionError を送出。
  - OrderRecord.transition_to() により state の変更とオプションフィールド（broker_order_id / filled_qty / avg_fill_price / error_message）更新を行い、updated_at を UTC 現在時刻で更新。
- OrderManager（外向け API）
  - create_order: signal_id の重複（アクティブ注文）検出。DB 側の部分ユニークインデックス違反を DuplicateOrderError に変換。
  - send_order: 2相永続化の戦略を採用（OrderSent を永続化→ broker 送信→ broker_order_id を先にコミット→ OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化し、クラッシュ後の再照合（reconciliation）に耐える設計。
  - sync_order: broker の状態取得による同期ロジック（部分約定の増分更新や OrderSent → Filled のケースで一時的に OrderAccepted を挟む等）。
  - cancel_order: キャンセル不可能な状態の判定と、broker 側 cancel 呼び出し→ Cancelled 遷移を実装。
- Broker クライアント
  - KabuStationClient を実装（httpx を使用する同期クライアント）。トークン取得の遅延初期化、401 時のトークン再取得＋再試行、429/5xx のエラー変換を実装。レスポンス JSON のパース失敗を BrokerAPIError に変換。
  - websocket を使った push 受信ループ（stream_push）を前提にした設計をサポート。
- リスク管理 / リコンシリエーション / 監視連携
  - ExecutionEngine が RiskManager、Reconciler、OrderRepository、OrderManager を組み合わせて動作する設計を実装。Gate1/2/3 による実行制御（Rate Limit / Circuit Breaker / ドローダウン監視）。
  - position_entries の更新（約定予定日＝翌営業日を用いる）など、ポジション追跡のための DuckDB 操作を含む。
- DB 周り
  - DuckDB と SQLite の併用を採用。duckdb は分析用途、sqlite は監視・履歴用途で、paper_trading 時には別 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
  - 監視DB の初期化ヘルパー（init_monitoring_db）呼び出しを組み込み、冪等にテーブル存在を保証。
- ユーティリティ
  - プロセス優先度設定（set_process_priority）とログ設定（setup_logging）ユーティリティを利用するよう統合。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- config_setup で .env に機密情報（トークン・パスワード）を書く旨を明示し、.env を Git に含めない注意喚起を追加。

Notes / 実装上の注意
- validate_config と Settings の両方で KABUSYS_ENV / LOG_LEVEL の妥当性チェックを行っているため、起動前の検証と実行時の両段階で誤った設定を検出可能。
- send_order の 2相永続化設計により、クラッシュやタイムアウトが発生しても Reconciler 経由で状態回復を試みられるようにしている（Issue #32 を意識した実装）。
- Monitoring は run_monitoring の実装上、環境に関わらず production 用 sqlite_path を使用する仕様となっている点に注意。
- .env のパースは実用上の様々なケース（クォート内のエスケープ、インラインコメント）に対応するよう実装されているが、特殊ケースでは期待通りに動作しない場合があるため重要なキーは明示的に検証することを推奨。

今後の予定（例）
- 非同期 HTTP クライアント（httpx.AsyncClient）への移行オプションを検討。
- より厳密な対話式入力（シークレット入力非表示、パスワード確認）の改善。
- validate_config による YAML スキーマ検証（PyYAML に加え JSON Schema 等の導入）や config/*.yaml の必須チェック強化。