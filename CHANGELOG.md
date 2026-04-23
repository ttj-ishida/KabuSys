# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本ファイルの内容はコードベースから推測して作成した要約です。

## [0.1.0] - 初版リリース
リリース日: 未設定

### Added
- パッケージ初期実装として主要コンポーネントを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を定義。
  - 設定読み取り/管理
    - src/kabusys/config.py
      - Settings クラスを実装し、環境変数から各種設定値を取得するプロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、PID/kill flag 関連、閾値など）。
      - .env 自動ロード機能を追加（優先順位: OS 環境変数 > .env.local > .env）。OS 環境変数を上書きしない保護機構を備える。
      - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い等）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途など）。
      - 設定が無い場合に例外を投げる _require() を提供。
  - 対話式設定ウィザード
    - src/kabusys/config_setup.py
      - .env の初期作成・更新を支援する対話式ウィザードを追加。シークレット入力・選択肢・デフォルト値をサポート。
      - 生成される .env のテンプレートと注意書きを出力（.env を Git にコミットしないよう明記）。
  - 設定検証 CLI
    - src/kabusys/validate_config.py
      - .env および config/*.yaml の設定不備を起動前にチェックする CLI を実装。
      - 必須環境変数チェック、プレースホルダ値検出、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス親ディレクトリ存在チェック、config/*.yaml の存在/パース（PyYAML が無ければスキップ）を行う。
      - KABUSYS_ENV=live のときの追加ガード（LINE 通知の未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
      - --strict オプションで警告を FAIL として扱うモードを提供。
  - 実行スクリプト（本番運用向け）
    - src/kabusys/run_execution.py
      - ExecutionEngine を使った発注セッション起動スクリプトを追加。プロセス優先度設定、停止フラグ検出、PID/stop flag の取り扱い、DB 接続（paper_trading は専用 SQLite を使用）を行う。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視 DB 初期化、stop flag 検出をサポート。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
  - 発注・状態管理コア
    - src/kabusys/execution/order_record.py
      - OrderState 列挙、OrderRecord データクラス、状態遷移ロジック（transition_to）を実装。許可されない遷移時には InvalidStateTransitionError を投げる。
    - src/kabusys/execution/order_manager.py
      - OrderManager を実装。create_order / send_order / sync_order / cancel_order を提供。
      - DuplicateOrder の検出（signal_id による部分ユニーク制約の取り扱い）を実装。
      - send_order はクラッシュ耐性を考慮した 2 相永続化を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。OrderSentPendingError の扱いなどを実装。
      - sync_order では broker 側の状態を照合して適切に遷移を行い、部分約定の進行では filled_qty / avg_fill_price を更新する。
      - cancel_order は終端状態のチェックと broker 呼び出しを経て Cancelled に遷移。
  - 発注エンジン
    - src/kabusys/execution/execution_engine.py
      - ExecutionEngine を実装。シグナル読み込み（DuckDB）、Gate による検査、発注フロー、WebSocket push ドレイン、リコンシリエーション、PID/killing の扱いを提供。
      - Gate の設計:
        - Gate 1: シグナルレベル検査（リスクチェック）
        - Gate 2: エグゼキューションレベル（API レート制限 / サーキットブレーカー、3 回リトライ）
        - Gate 3: ドローダウン監視（NG の場合 kill_switch を発動）
      - kill_switch 発動時は全 active 注文をキャンセルし、エンジンを停止する。
      - WebSocket スレッドを持ち、push 通知を _push_queue に投入する設計（broker が stream_push をサポートしない場合はスキップ）。
      - 発注成功時の position_entries の書き込み（fill_date=翌営業日）や監視DB へのトレードイベント記録を行う。
      - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START に応じて自動クリアまたは起動拒否。
  - broker クライアント（kabu station）
    - src/kabusys/execution/kabu_client.py
      - KabuStationClient を実装。httpx(Client) を使用して同期的に REST API を扱う。
      - トークン管理（遅延初期化、401 での再取得とリトライ）、レスポンス JSON パースのエラーハンドリング、429（RateLimit）/5xx/401 のエラー分類を実装。
      - WebSocket push 受信用の依存（websocket）を使用する窓口を用意。
  - 監視 DB 初期化 / SystemMonitor 連携（呼び出し箇所を実装）
    - run_monitoring / run_execution から monitoring_db 初期化を呼ぶコードを追加（init_monitoring_db）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- .env 自動ロードで OS 環境変数を保護するため protected set を導入し、既定の OS 環境変数を .env.local/.env で上書きしないように実装。

### Notes / 実装上の重要点（ユーザ向け）
- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、実行は MockBroker を利用する想定で、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に書き込む。本番 DB と明確に分離される。
- 監視:
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは常に本番 DB を見る設計）。
- .env パース:
  - export KEY=val 形式、クォート内のエスケープ、行内コメントを考慮しているため、一般的な .env の記述に対応。
- 起動ガード:
  - kill.flag の存在による二重起動防止や、KILL_FLAG_CLEAR_ON_START による自動クリア動作が組み込まれているため、本番起動時は当該値を十分に確認すること。
- 設定検証:
  - validate_config を使うことで事前に設定漏れや明らかなミス（プレースホルダ残し、無効な列挙値、YAML パース失敗等）を検出できる。CI で --strict を使えば警告も失敗扱いにできる。

もしリリース日や追加の変更履歴（バグ修正、パフォーマンス改善、互換性情報など）を本来のコミットログや PR から補完できる場合は、それらを反映して更新してください。