# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。  

## [0.1.0] - 2026-04-22

初回リリース。日本株自動売買システム KabuSys の基本機能を提供します。

### Added
- 環境/設定管理
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加（kabusys.config）。
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。OS 環境変数は保護され、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env のパースは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内でのバックスラッシュエスケープ
    - クォートなし行でのインラインコメント（直前が空白/tab の場合のみ）
- 設定ウィザード CLI
  - 対話式で .env を作成/更新する `kabusys.config_setup` を追加。項目ごとの説明、デフォルト、選択肢、シークレット表示、保存前の確認をサポート。
  - .env ファイルのテンプレート生成ロジックを追加（書き込み時に注意書き、カテゴリ別のコメントを出力）。
- 設定検証 CLI
  - 起動前に .env と config/*.yaml を検証する `kabusys.validate_config` を追加。
  - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、データベースパスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合の）パース検証を実行。
  - --strict オプションで警告を FAIL として扱い exit(1) で終了するモードを提供。
  - PyYAML が未インストールの場合は YAML コンテンツ検証をスキップして警告を出力。
- 実行スクリプト
  - ExecutionEngine 起動スクリプト `kabusys.run_execution` を追加。paper_trading 時は専用の paper DB を使用して本番 DB と分離。
  - SystemMonitor ポーリングスクリプト `kabusys.run_monitoring` を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。
  - 両スクリプトはプロセス優先度設定（High）を行い、停止フラグの監視と安全な DB クローズを実装。
- 発注/実行基盤
  - OrderRecord（純粋ビジネスロジック）と OrderState（状態列挙）を実装。状態遷移検査と updated_at の自動更新を提供（kabusys.execution.order_record）。
  - OrderRepository と連携する OrderManager を実装（kabusys.execution.order_manager）。
    - create_order: signal_id の重複チェック（DB 部分ユニーク制約違反も重複として扱う）。
    - send_order: 2 相永続化を意識した送信フロー（OrderSent の永続化 → ブローカー呼出し → broker_order_id 保存 → OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: ブローカー側の状態を取得してローカル状態へ同期。部分約定時の部分更新もサポート。
    - cancel_order: 終端状態ではキャンセル不可と判定し例外を投げる。broker_order_id があれば API 呼び出しを実施。
  - ExecutionEngine を実装（kabusys.execution.execution_engine）:
    - シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）のセッション制御。
    - Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル／レート制限）、Gate 3（ドローダウン監視）を導入し、リスク検査により発注制御や kill_switch を発動可能。
    - size_multiplier の適用、発注失敗/保留時の扱い、position_entries の更新（DuckDB を利用）や監視 DB への発行ログ出力を行う。
    - WebSocket push からの通知処理で broker_order_id をキーに同期を行う設計。
    - kill.flag の扱い: 起動時の KILL_FLAG_CLEAR_ON_START 設定により自動クリア可（Settings 経由で取得）。
- ブローカー/クライアント実装
  - KabuStation REST API クライアントを実装（kabusys.execution.kabu_client）。
    - httpx を使用した同期実装、トークン取得の遅延初期化と 401 時のトークン再取得（1 回リトライ）、HTTP ステータスに基づく独自例外マッピング（認証エラー、レート制限、サーバーエラーなど）。
    - WebSocket push（stream_push）を想定した stream_push フックの利用に対応。
- モニタリング
  - Monitoring DB 初期化ユーティリティ（init_monitoring_db）を呼び出して監視用テーブルを確実に作成。
  - run_monitoring では監視ループ中に例外をログ出力しつつ継続する設計。

### Changed
- 設定バリデーションを Settings プロパティにて厳密化
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを設定プロパティで実施し、不正値で ValueError を送出するようにした。
  - PAPER_FILL_MODE の検証を追加（有効値: instant, partial, never, reject）。
- DB パス取り扱い
  - paper_trading 環境では Execution は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を用い、本番 sqlite_path と分離するように実装。

### Fixed
- 発注フローのクラッシュ耐性向上
  - send_order における broker 呼び出し前後の永続化順序を明確化し、クラッシュ時に OrderSent や broker_order_id が残るケースを想定して Reconciliation で回復可能に設計（Issue を想定した修正点の反映）。
- .env パースの不整合を改善
  - クォート内のエスケープ処理、export プレフィックスの扱い、インラインコメント判定を強化して一般的な .env 形式に対応。

### Security
- .env に対する注意書きを config_setup の出力に追加（.env を Git にコミットしない旨の明示）。

### Notes / Usage
- 設定ウィザード:
  - python -m kabusys.config_setup で対話的に .env を生成/更新できます。
- 設定検証:
  - python -m kabusys.validate_config で起動前チェック。--strict で警告を FAIL 扱いにできます。
- 実行:
  - python -m kabusys.run_execution および python -m kabusys.run_monitoring を実行してそれぞれエンジン／監視を開始します。
- 依存:
  - config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われます。PyYAML がない場合は検証をスキップして警告が出ます。

## 未定義 / 今後
- 既知の改善点（今後のリリース候補）
  - 非同期 httpx.AsyncClient への対応（非同期化）
  - より詳細な監視メトリクスの追加、監視アラートの外部通知強化
  - Reconciliation・リスク制御ロジックの追加ユニットテスト強化

（初回リリースのため破壊的変更はありません）