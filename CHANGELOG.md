# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 全体
  - 初期リリース相当の機能群を追加。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。
- 設定・運用関連
  - Settings クラスを実装し、環境変数経由でアプリ設定を取得する API を提供（kabusys.config）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env の対話式ウィザードを実装（kabusys.config_setup）。.env の作成・更新を支援する CLI。
  - 設定検証 CLI を実装（kabusys.validate_config）。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース等を事前検査可能。--strict オプションで警告を失敗扱いにできる。
- 実行 / 監視用スクリプト
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。paper_trading 環境では専用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
  - モニタリング用ポーリングスクリプトを追加（kabusys.run_monitoring）。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- 発注周り（Execution）
  - ExecutionEngine を実装（kabusys.execution.execution_engine）。シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）を行うセッション制御を提供。
  - OrderManager を実装（kabusys.execution.order_manager）。signal_queue からのシグナルを受け、Broker API 経由で発注・同期・キャンセルを行う外向き API を提供。
  - OrderRecord（状態遷移ロジック）を実装（kabusys.execution.order_record）。Order State Machine を純粋なビジネスロジックとして実装し、不正遷移を検出して例外を投げる。
  - Reconciliation を想定した設計（OrderSent の二相永続化等）を実装。クラッシュ耐性を考慮した発注フローを採用。
  - 発注フローでのイベントを監視 DB にログできる仕組み（monitoring_db への書き込みフック）を実装。
  - RiskManager を利用した Gate1/2/3 のリスクチェックを組み込み（レート制限・サーキットブレーカー・ドローダウン監視等）。
  - paper_trading 用の fill_mode（PAPER_FILL_MODE）および paper_trading 用 SQLite のパス設定を追加。
- ブローカークライアント
  - KabuStationClient を実装（kabusys.execution.kabu_client）。httpx を利用した同期 REST クライアント、トークン自動取得・401 リトライや 429（レート制限）の例外ラップを実装。
  - WebSocket push 受信用 API（stream_push）を想定した WebSocket ワーカースレッド実装を ExecutionEngine に追加（push を受けて同期処理へ投入）。

### 変更 (Changed)
- 環境変数の扱い
  - .env パーサの挙動を強化：export 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの取り扱いなどを改善。これにより .env に書かれたトークン等の取り扱いが正確に行われる。
  - .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。.env.local は override=True で .env を上書き可能。
- 発注フローの堅牢化
  - send_order の処理を二相に分割し、OrderSent を永続化 → ブローカー呼び出し → broker_order_id を永続化 → OrderAccepted に遷移、とすることでクラッシュ時の復旧（Reconciliation）を容易に。
  - OrderSentPendingError（注文番号は返るが約定しないケース）を特別扱いし、broker_order_id を永続化したうえで OrderSent のまま残す設計を採用。
- ExecutionEngine の振る舞い
  - kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START の扱いを整理。起動時に kill.flag が残っている場合の挙動を明確化（自動クリア or 起動拒否）。
  - PID ファイルの書き込み、プロセス優先度の設定（set_process_priority("high")）を起動時に実施するようにした。
  - push ドレイン処理時に portfolio valuation を行い Gate 3 を評価、NG の場合は kill_switch を発動するようにした（spurious push でも評価を行う設計）。
- 監視処理
  - run_monitoring は環境を問わず本番用 sqlite_path を使用するように明記（監視は本番 DB を参照する設計）。
  - MONITOR_POLL_INTERVAL の無効値扱いはデフォルトにフォールバックし、0 以下は不正としてログを出すように改善。

### 修正 (Fixed)
- 設定検証（validate_config）
  - 必須環境変数未設定やプレースホルダ値（例: *_here, your_value）を検出して警告/エラー出力するように実装。
  - PyYAML 未インストール時の挙動を安全にフォールバックし、YAML のパース検証はスキップして警告を出す設計に変更。
  - config/*.yaml が存在しない場合の案内メッセージ（python scripts/generate_config.py で生成可能）を追加。
- OrderRepository / OrderManager 周り
  - DB の UNIQUE constraint による DuplicateOrder を適切に DuplicateOrderError に変換して扱うように修正（signal_id に関する部分ユニーク制約の考慮）。
  - sync_order の同一状態更新時に filled_qty / avg_fill_price の変化のみのケースを検出して更新するロジックを追加（transition_to を使わず差分更新を行う）。
- KabuStationClient
  - トークン取得・HTTP レスポンスの JSON パース失敗時に適切な BrokerAPIError を投げるように改善。
  - 401 後にトークン再取得してリトライし、それでも 401 の場合は認証エラーとして扱うよう修正。
  - 429 レスポンスは RateLimitError として区別してスロー。

### 破壊的変更 (Breaking Changes)
- なし（初期リリース相当）。ただし Settings のプロパティは未設定時に ValueError を投げるため、既存の実行環境では .env の整備が必須。

### セキュリティ (Security)
- 機密値（トークン・パスワード）は対話ウィザードおよび .env 書き出し時にマスク表示。.env ファイルは Git にコミットしない旨を README ヘッダで強調。

### 注意事項 / マイグレーション
- .env の書式が改善されているため、既存の .env に特殊なエスケープやコメントがある場合は validate_config での検証や Settings の自動読込結果を確認してください。
- 本番環境（KABUSYS_ENV=live）での起動前に validate_config の実行を推奨（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告等がある）。
- paper_trading を使用する場合は PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等の設定を確認のこと。

---

その他の改善やバグ修正はソース内のドキュメント（各モジュールの docstring / コメント）を参照してください。