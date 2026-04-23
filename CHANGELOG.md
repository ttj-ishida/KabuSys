# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付や細かいコミット情報はソースコードから推測して記載しています。

全般的な注意:
- 本パッケージは環境変数とローカル設定ファイル（.env, config/*.yaml）を中心に動作します。
- .env は決してリポジトリにコミットしないでください（config_setup にも注意書きあり）。

## [Unreleased]

- なし（このCHANGELOGは現行のコードベースのスナップショットから作成しています）。

## [0.1.0] - 2026-04-23

初回リリース想定。以下の主要機能・改善・修正を含みます。

### 追加 (Added)
- 設定・環境変数周り
  - Settings クラスを導入し、環境変数からアプリケーション設定を集中管理（例: jquants_refresh_token, KABU_API_PASSWORD, DBパス等）。
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env と .env.local を自動読み込みする仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env ファイルのパーサーを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。

- 設定ウィザード・検証 CLI
  - config_setup CLI（python -m kabusys.config_setup）を追加。対話式に .env を生成・更新できるウィザードを提供。シークレットはマスク表示、デフォルトや選択肢をサポート。
  - validate_config CLI（python -m kabusys.validate_config）を追加。起動前に必須環境変数・config/*.yaml・DBパス・KABUSYS_ENV 等の妥当性チェックを行う。--strict フラグで警告も失敗として扱える。

- 実行・監視用スクリプト
  - run_execution スクリプト（ExecutionEngine の起動エントリ）を追加。paper_trading 環境では専用の paper_trading DB を使用するよう分離。
  - run_monitoring スクリプト（SystemMonitor のポーリングループ）を追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視用 DB 初期化処理を実装。

- 発注・実行基盤
  - ExecutionEngine を実装。シグナル取得、Gate1/Gate2/Gate3 に基づくリスク検査、発注ループ（シグナル処理→push ドレイン）、WebSocket push 処理を含む。
  - OrderRecord（状態遷移の純粋ロジック）を実装。状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移を定義。InvalidStateTransitionError を導入。
  - OrderManager を実装。create/send/sync/cancel の外向き API を提供。重複注文検出（同一 signal_id の active 注文をブロック）や、OrderSent の永続化→broker 呼び出し→broker_order_id 永続化→OrderAccepted 更新という「2相永続化」戦略でクラッシュ耐性を高める。
  - Reconciler / リコンシリエーション呼び出しの統合（ExecutionEngine 起動時に実行可能、同期結果のログ出力）。
  - 発注時の監視記録（監視DBへの trade_event ログ）を統合可能に。

- ブローカークライアント
  - KabuStationClient を実装（httpx を使用）。トークン取得を内部で管理し、401 時の自動再取得・リトライを行う。HTTP ステータスに応じたエラー変換（RateLimitError 等）を実装。
  - WebSocket push の受け取り（stream_push）により push ペイロードを処理可能な設計をサポート。

- 監視・運用
  - stop_requested.flag / kill.flag / PID ファイルを利用したプロセス制御（起動時・ループ内での停止検知）。
  - プロセス優先度設定ユーティリティを呼び出すフローを追加（起動時に優先度を "high" に設定）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様を採用（監視は常に本番DBで観測するため）。

- Paper trading 対応
  - paper_trading 環境で MockBrokerClient を使い、paper_trading 用の SQLite に分離して記録する設計を導入。

### 変更 (Changed)
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。OS 環境を保護するため protected set を使用して上書きを制御。
- ExecutionEngine のシグナル処理・キャンセルロジック強化:
  - size_multiplier の適用は BUY のみ（SELL は保有分を売るため縮小しない）。
  - Gate2 のレート制限でリトライ（最大3回）を実装し、Circuit Breaker 発動時はシグナルループを停止（ドレインループは継続）する振る舞いに。
  - 発注のタイムアウト/保留（OrderSentPendingError）を区別して取り扱い、pending 状態は永続化して Reconciliation の対象とする。
- log_level / env の検証を Settings 側でも行い、不正値は ValueError を投げるように。
- PID ファイル作成時に親ディレクトリを自動作成し、起動終了時にファイルを確実に削除するよう改善（missing_ok を使用）。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL のパース・検証ロジックを追加。0 以下や不正値は警告を出してデフォルトにフォールバックするようにし、time.sleep に渡して ValueError になる事態を防止。
- config/*.yaml の検証処理で PyYAML 未インストール時に適切に警告を出し、パース失敗時はエラーとして扱うように。
- .env ファイル読み込み時にファイルアクセスエラー発生時は警告を出して処理を継続するように。
- OrderRepository 側の UNIQUE 制約違反（signal_id に対する部分ユニーク）を検出して DuplicateOrderError に変換することで、DB 制約起因の二重化を適切に扱う。

### セキュリティ (Security)
- config_setup が生成する .env ファイルに対して「絶対に Git にコミットしないこと」を明記。
- config_setup のシークレット項目はウィザード表示時にマスクして提示。

### 既知の制限 / 備考 (Known issues / Notes)
- YAML パース検証は PyYAML の有無に依存する（未インストール時は検証をスキップして警告のみ表示）。
- KabuStationClient は同期 httpx.Client を使用しているため、将来的に非同期対応が必要な場合は httpx.AsyncClient への移行を想定。
- 一部の例外（BrokerAPIError 等）は OrderManager.send_order 内で意図的に捕捉せず、OrderSent のまま残して list_uncertain()/reconciliation の対象にする設計になっている（クラッシュ安全性のトレードオフ）。
- 実際の運用では .env の初期化 → validate_config による検証 → 本番実行（run_execution/run_monitoring）の順で使うことを推奨。

---

この CHANGELOG はソースコード内の実装・コメントから推測して作成しています。差分（実コミット履歴や追加の変更点）がある場合は適宜更新してください。