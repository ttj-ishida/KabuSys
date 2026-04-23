CHANGELOG
=========

すべての重要な変更点を記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys の設定・起動・実行・監視に関する主要機能を追加。
- 設定管理
  - Settings クラスを追加。環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill Flag 等）を取得するプロパティ群を提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。読み込み優先度は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env のパース機能を強化（export KEY=、シングル/ダブルクォート内のエスケープ、行末コメントの扱いなどに対応）。
  - _load_env_file で「override」と「protected」オプションを導入し、OS 環境変数を保護しつつ .env.local で上書き可能にした。
  - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等、Paper Trading 関連の設定を分離して提供。
- 設定ウィザード
  - config_setup CLI（python -m kabusys.config_setup）を追加。.env を対話的に生成・更新するウィザードを実装。秘密値はマスク表示、選択肢・デフォルト表示をサポート。
  - .env を書き出すテンプレートをセクション分けして出力（J-Quants / kabu / LINE / DB / Kill Switch 等）。
  - .env を作成後に validate_config 実行を推奨するメッセージを表示。
- 設定検証ツール
  - validate_config CLI（python -m kabusys.validate_config）を追加。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検出（末尾が "_here" または "your_value" の場合は警告）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（有効値を限定）。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック（存在しない場合は警告。起動時に自動作成される可能性を案内）。
  - config/*.yaml の存在確認と、PyYAML がインストールされている場合はパース検証を実施（未インストール時はスキップして警告）。
  - KABUSYS_ENV=live 時の追加ガード（LINE トークン類の未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
  - --strict オプションで警告を FAIL と扱い exit(1) を返す機能を実装。
- 実行 / 監視ランナー
  - run_execution スクリプトを追加（ExecutionEngine を起動）。
    - Paper Trading 時は専用 SQLite（paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度設定（set_process_priority）を起動時に実行。
    - PID ファイル出力、停止フラグ（data/stop_requested.flag）の監視、停止時の安全なシャットダウンを実装。
  - run_monitoring スクリプトを追加（SystemMonitor のポーリングループ）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用するように設計。
- Execution / Order 実装
  - ExecutionEngine を追加。シグナル読み込み（DuckDB）→ Gate1/Gate2 リスクチェック → 発注 → push ドレイン（WebSocket）というセッションモデルを提供。
    - シグナル処理時間帯（デフォルト 8:50-9:10）とマーケット終了（15:30）を組み込み。
    - WebSocket push を別スレッドで受け取り、_push_queue へ投入。プッシュは drain で処理。
    - kill_flag 存在時の起動拒否/自動クリア（KILL_FLAG_CLEAR_ON_START による）と、kill_switch 発動時の全 active 注文キャンセル処理を実装。
    - 起動時に Reconciler によるリコンシリエーションを試行（オプション）。
    - 発注成功時に position_entries へ約定予定日を記録（buy は entry、sell は sell_date 更新）。
    - 発注レイテンシを監視DBへ記録する仕組みを組み込み可能（MonitoringDB 経由）。
  - OrderRecord（状態マシン）を追加。OrderState の列挙と許可遷移を定義。transition_to による遷移検証と更新タイムスタンプ自動更新を実装。
  - OrderManager を追加。create_order / send_order / sync_order / cancel_order の主要フローを実装。
    - create_order は signal_id に対する重複 active 注文チェックを実施し、UUID を client_order_id に採番。
    - send_order はクラッシュ耐性を考慮した「OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化（state は Sent）→ OrderAccepted に遷移」などの 2 相永続化フローを実装。
    - OrderSentPendingError（注文番号は発行されたが約定しない/保留）を扱い、broker_order_id を永続化したまま OrderSent のまま残す挙動を実装。
    - sync_order は broker 側ステータスを取得して状態を同期。部分約定の進行はフィールド直接更新で対応。
    - cancel_order はキャンセル不可能な状態（Closed / Cancelled / Rejected / Filled）を考慮して例外を返す。
    - DuplicateOrderError を定義して DB 制約違反や既存 active 注文を表現。
- ブローカークライアント
  - KabuStationClient を追加。
    - httpx を使用した同期 REST クライアント実装（将来は httpx.AsyncClient に切り替え可能）。
    - トークン取得の遅延初期化、自動再取得（401 時のリトライ）を実装。
    - レスポンスの JSON パース失敗やネットワーク例外を BrokerAPIError に変換。429 レスポンスを RateLimitError として扱う。
    - kabu station の状態コードを内部状態 ("open"/"partial"/"filled"/"cancelled"/"rejected") にマッピング。
- リスク / レート制御 / モニタリング
  - RiskManager / Gate チェック群、Circuit Breaker、API 成功/失敗記録に基づく Gate2 の扱いを統合。
  - push を受けた際に Gate3（ドローダウン監視）を実行し NG の場合は kill_switch を発動。
- DB 初期化
  - init_monitoring_db を呼ぶことで監視用 SQLite のテーブル作成を保証（冪等）。
- ロギング / プロセス制御
  - setup_logging と set_process_priority を統合した起動シーケンスを採用。モジュール単位のログ名とログレベル設定をサポート。

Changed
- .env 読み込みはパッケージ内の __file__ を基点にプロジェクトルートを決定するため、CWD に依存せず配布後も安定して動作するよう設計。
- ExecutionEngine のセッション制御を明確化（kill.flag 検査・PID 書き込みの順序などを整理）。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使うように明示。

Fixed
- MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックするようにし、time.sleep に渡して ValueError になる問題を回避。
- .env パーサー: クォート内のエスケープ処理や inline コメントの扱いを改善し、実務で使いやすくした。
- send_order のクラッシュ時シナリオを考慮した 2 段階永続化により、OrderSent 状態で残るケースからの回復性を改善（reconciliation を容易にする）。

Security
- .env は絶対に Git にコミットしない旨を config_setup のヘッダに明記。
- デフォルトで機密値はウィザード上でマスク表示（出力は平文の .env に保存するため注意喚起を行う）。

Deprecated
- なし

Removed
- なし

Notes
- 本リリースはコードベースから推測して作成した初期 CHANGELOG です。将来的な変更（API 仕様の詳細変更やブローカー実装差異など）に合わせて更新してください。