# Changelog

すべての変更は Keep a Changelog の指針に従って記載しています。  
慣例により、非互換な変更は破壊的変更として明確に記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
最初の安定リリース。KabuSys のコア設定管理・監視・発注エンジンの基礎機能を実装しました。

### 追加 (Added)
- 環境設定管理
  - Settings クラスを実装し、環境変数から各種設定をプロパティ経由で取得可能にしました（J-Quants / kabu API / LINE / DB パス / システム設定 / 監視閾値など）。
  - .env 自動読込機能: プロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を自動ロード。OS 環境変数の保護（既存値を上書きしない / 保護セット）をサポート。
  - 環境変数パーサーを強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いを実装。

- 対話式設定ウィザード
  - `kabusys.config_setup.run_wizard`（CLI: python -m kabusys.config_setup）で .env の作成・更新を支援するウィザードを追加。
  - ウィザードは複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークンなど）を用意し、シークレット項目はマスク表示します。
  - .env ファイルへのテンプレート書き出し機能を実装。

- 設定検証ツール
  - `kabusys.validate_config`（CLI: python -m kabusys.validate_config）を追加。
  - 必須環境変数の未設定チェック、プレースホルダ値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML が存在する場合は）パース確認、本番環境向け追加ガードを実装。
  - `--strict` オプションで警告も失敗扱い（exit code=1）にできます。

- 実行/監視用エントリポイント
  - run_execution（python -m kabusys.run_execution）: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading 環境時に専用 SQLite（paper_trading.db）を使用して本番 DB と分離します。
  - run_monitoring（python -m kabusys.run_monitoring）: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。

- Execution エンジンと発注フロー
  - ExecutionEngine を実装。シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）をサポート。
  - EngineConfig により当日の target_date / 時間帯を設定可能。
  - シグナル読み込みは DuckDB から行い、size_multiplier の適用や買い専用の数量調整（単位切り捨て）を実装。
  - Gate1（シグナルレベル）、Gate2（実行レベル / レート制限・サーキットブレーカー）、Gate3（ポートフォリオ指標・ドローダウン）という三段階のリスクチェックを実装。Gate2 ではリトライと CB に応じた動作を行います。
  - kill_switch により全アクティブ注文をキャンセルし、ループ停止する機能を実装。
  - WebSocket（broker.stream_push）を用いた push 受信を別スレッドでサポートし、push をキュー化して処理。

- 注文管理コンポーネント
  - OrderRecord: 注文状態を表す state machine（OrderState 列挙、許可遷移定義、transition_to 実装）を追加。DB に依存しない純粋ロジック。
  - OrderRepository（参照）と組み合わせる OrderManager を実装。create/send/sync/cancel の高レベル API を提供。
    - create_order: signal_id の部分ユニーク制約・重複チェック（DuplicateOrderError）を実装。
    - send_order: クラッシュ耐性を考慮した二相的永続化フロー（OrderSent へ先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted に遷移）を実装。OrderSentPendingError の扱いも含む。
    - sync_order: broker の状態を取り込み、状態遷移・部分約定情報の更新を行う。OrderSent→Filled/Partial の回復のため OrderAccepted を経由するロジックを実装。
    - cancel_order: キャンセル不可状態の検出、broker API 呼び出し、Cancelled への遷移を実装。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（httpx ベース、同期クライアント）。
  - トークン管理（遅延取得・自動再取得）、401 時のリトライ、429（RateLimitError）/500系のエラー判定、JSON パース失敗時の変換を実装。
  - WebSocket 受信用に websocket 経由の stream_push（任意）を想定する設計。

- 監視/ログ/ユーティリティ
  - 監視 DB 初期化（init_monitoring_db）の呼び出しを実装し、監視 DB への発注イベント記録を追加。
  - setup_logging, set_process_priority などのユーティリティ利用を標準化（起動時にプロセス優先度を high に設定するなど）。
  - PID・停止フラグ（data/stop_requested.flag, kill.flag, execution.pid）の取り扱いを実装。

### 変更 (Changed)
- 設定周りの堅牢化
  - .env の読み込み順序を OS 環境変数 > .env.local > .env にし、テストや CI での上書きを容易にしました。
  - Settings のプロパティで KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などの値検証を行い、不正な値は早期に例外を発生させるようにしました。

- DB/環境分離
  - paper_trading モード時には paper_sqlite_path（data/paper_trading.db）を使用して本番監視 DB と完全分離する動作に変更。

- 発注/リコンシリエーション設計
  - send_order の二相永続化と sync_order の回復フロー（Issue #32 を考慮）により、クラッシュ時の状態回復性を改善しました。

### 修正 (Fixed)
- .env のパースに関して以下の改善/修正を行いました:
  - export プレフィックスを許容。
  - 引用符付き値内のバックスラッシュエスケープを正しく解釈。
  - 非引用符値の行内コメント判定を「# の直前がスペースまたはタブのとき」に限定して誤判定を回避。

- ExecutionEngine のシグナル処理において、size_multiplier 適用後 qty が 0 になったシグナルをスキップすることで無駄な処理を避けるようにしました。

- run_monitoring/run_execution の終了処理で SQLite / DuckDB 接続を確実にクローズするようにしました。

### 破壊的変更 (Breaking Changes)
- なし（本バージョンは初期リリースのため互換性の遡及対象なし）。

### セキュリティ (Security)
- なし（公開済みの変更点の範囲では特記事項なし）。

---

開発方針や実装の意図、既知の制約（例: KabuStation がローカルで稼働している前提など）はコード内ドキュメント及びモジュール docstring に記載しています。今後のリリースでは以下を計画しています（例示）:
- 非同期対応（httpx.AsyncClient への移行）、
- より詳細な監視メトリクスと可視化用エクスポート機能、
- Broker API のテスト用モック・ファクトリーの拡充。