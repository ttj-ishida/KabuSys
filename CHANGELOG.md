# Changelog

すべての重要な変更点を Keep a Changelog の形式で記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: この CHANGELOG はリポジトリ内のコードから推測して生成しています。

## [Unreleased]

### Added
- 設定検証 CLI を追加 (`kabusys.validate_config`)
  - .env や config/*.yaml の設定不備を起動前に検出するコマンドラインツール。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、YAML パーサ（PyYAML が未インストールの場合は検証スキップ）などを実装。
  - `--strict` オプションにより警告を FAIL（exit 1）として扱える。
  - KABUSYS_ENV=live の場合に追加の「本番向けガード」を実施（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。

- 環境設定ウィザードを追加 (`kabusys.config_setup`)
  - 対話式で .env を初期作成 / 更新する CLI。
  - 選択肢、デフォルト、マスク表示（シークレット）のサポート。
  - 生成される .env のテンプレートには注意書き（Git にコミットしない等）を含む。

- 設定管理モジュール強化 (`kabusys.config.Settings`)
  - .env / .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml から検出）。
  - OS 環境変数を保護する `protected` 処理（既存 OS 環境変数は上書きされない）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env ファイルのパースを堅牢化（`export` プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメントの扱いなどに対応）。
  - 各種プロパティ（`jquants_refresh_token`, `kabu_api_password`, `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種しきい値等）を提供。
  - `PAPER_FILL_MODE` のバリデーション（有効値: "instant" | "partial" | "never" | "reject"）。
  - `env` / `log_level` の値検査を実装（無効値は例外）。

- Execution / Monitoring 起動スクリプトを追加・改善
  - `run_execution.py`
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、PID ファイル管理、停止フラグ検査、paper_trading 時の DB 分離（paper_trading 用 SQLite）を実装。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループを起動するスクリプト。`MONITOR_POLL_INTERVAL` によるポーリング間隔上書き、停止フラグ検出、SQLite / DuckDB 接続管理を実装。
  - 両スクリプトとも例外安全に DB 接続をクローズする。

- 発注周り（Execution）機能の実装・強化
  - OrderRecord: 状態機械（OrderState）と状態遷移ロジックを純粋なビジネスロジックとして実装。許可される遷移セットと `InvalidStateTransitionError` を定義。
  - OrderManager:
    - `create_order` / `send_order` / `sync_order` / `cancel_order` の外向き API を実装。
    - 同一 signal_id の重複注文検出（部分ユニークインデックス違反を DuplicateOrderError にマッピング）。
    - send_order はクラッシュ耐性を考慮した 2 段階永続化を行う（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）。
    - `OrderSentPendingError` の扱い（注文番号は記録するが状態は Sent のまま残し、呼び出し元へ伝播）。
    - `sync_order` による broker からの状態同期（部分約定時の数量・価格更新の扱いを含む）。
    - `cancel_order` はキャンセル不可能な状態を排除して API 呼び出し・状態遷移を実行。

  - ExecutionEngine:
    - シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を実装。
    - Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル・レート制限）、Gate 3（ドローダウン検査）を導入。Gate 3 NG なら kill_switch 発動。
    - kill_switch により全 active 注文を逐次キャンセルしループを停止する。
    - WebSocket push の受信を別スレッドで行い、受信 payload は内部キューへ投入、Engine 側で同期・Gate3 評価を実施。
    - 発注時に monitoring DB へトレードイベントを記録するフックを追加（`monitoring_db.log_trade_event` を使用、失敗しても発注フローは継続）。

- broker クライアント実装（kabu station）
  - `KabuStationClient` を実装（httpx 同期クライアント）。
  - トークン取得の遅延初期化、自動再取得（401 時に再トライ）、HTTP エラーコードに基づく例外マッピング（401→認証エラー、429→RateLimitError、5xx→サーバーエラー）を実装。
  - レスポンス JSON パース失敗を適切に BrokerAPIError に変換。
  - WebSocket（push）連携向けの `stream_push` を想定した設計。

### Changed
- .env パーサの強化により、従来曖昧だった引用符やコメントの扱いが明示的に処理されるようになった。
- settings の自動ロード順序や上書きルールを明確化（OS 環境変数 > .env.local > .env）。

### Fixed
- .env 読み込み時のエラーを warnings として通知するように改善（読み込み失敗でプロセスが異常終了しないように対応）。

### Security
- .env を生成するテンプレートに「絶対に Git にコミットしないこと」の注意書きを追加。

---

## [0.1.0] - 2026-04-23

初期リリース。

### Added
- パッケージ初期版として上記の全機能を実装:
  - 設定管理（.env 自動ロード、堅牢なパース）、Settings クラス
  - 環境設定ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - Execution / Monitoring の起動スクリプト（run_execution, run_monitoring）
  - ExecutionEngine、OrderManager、OrderRecord、Reconciler（骨格）、RiskManager（連携点）
  - KabuStationClient（REST/WebSocket の骨格）
  - DuckDB / SQLite を用いたデータ管理の統合ポイント
  - PID / stop flag / kill switch による運用周りの制御

### Changed
- （初期リリース）なし

### Fixed
- （初期リリース）なし

---

注記:
- コードから推測して記載しているため、実際のコミット履歴・作者意図と差異があります。必要であれば各ファイル内の docstring / ログ文言等を基にさらに詳細な履歴を作成できます。