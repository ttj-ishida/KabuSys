# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従い、セマンティック バージョニングを採用します。

## [Unreleased]
- なし（次回リリースに向けた未公開の変更点がある場合ここに記載します）

## [0.1.0] - 2026-04-21
初回公開リリース。主要な機能・コンポーネントを実装しました。

### 追加 (Added)
- 全体
  - KabuSys の初期バージョンを公開。日本株自動売買システムのコアコンポーネントを含む。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定関連
  - Settings クラスを実装し、環境変数経由での設定取得を提供（J-Quants・kabu API・DB パス・監視閾値など）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env/.env.local の読み込み優先度を実装（OS 環境変数 > .env.local > .env）、OS 環境変数は保護（上書き防止）。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い）。

- 設定ツール
  - 対話式ウィザード `kabusys.config_setup` を追加。`.env` の作成/更新を対話的に支援。
  - ウィザードで生成される `.env` テンプレートには注意書き（Git にコミットしない）を含む。

- 設定検証
  - `kabusys.validate_config` CLI を追加。.env と config/*.yaml の設定不備を起動前に検出。
  - `--strict` オプションを追加（警告も失敗として exit(1)）。
  - PyYAML 未インストール時は YAML 内容検証をスキップするが警告を出力するように実装。

- 実行・監視スクリプト
  - `run_execution.py`：ExecutionEngine を起動するエントリポイントを追加。paper_trading 環境では専用の SQLite を使用し、本番 DB と分離。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するエントリポイントを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。

- 発注系（Execution）
  - ExecutionEngine（信号読み取り → Gate チェック → 発注 → WebSocket プッシュ処理のドレイン）を実装。
  - EngineConfig によりターゲット日や発注時間帯を設定可能（デフォルト: 発注 8:50-9:10、市場クローズ 15:30）。
  - OrderManager を実装：シグナルからの注文生成、送信、同期、キャンセルの外向き API。
  - OrderRecord（状態遷移ロジック）を実装：OrderState 列挙・許可遷移・不正遷移時の例外（InvalidStateTransitionError）。
  - 二相永続化設計：OrderSent 前後のクラッシュ耐性を考慮し、broker_order_id の先保存 → 状態遷移の順で保持することで Reconciliation による復旧が可能。
  - DuplicateOrderError による同一 signal_id の重複防止（DB の部分ユニーク制約違反を適切に変換）。
  - Reconciler フックを ExecutionEngine 起動時に実行可能（起動時リコンシリエーションをサポート）。

- ブローカー実装（kabu）
  - KabuStationClient を実装（httpx 同期クライアント）。トークン取得・自動再取得、401 リトライ、429（RateLimit）・5xx エラー判定を実装。
  - send_order / cancel_order / get_order_status を実装（レスポンスの JSON パースやエラーを BrokerAPIError/OrderRejectedError 等に翻訳）。
  - WebSocket プッシュ受信用の stream_push インターフェースを想定（ExecutionEngine の WebSocket ワーカーと連携）。

- 監視・ロギング・ユーティリティ
  - 監視 DB 初期化（init_monitoring_db）を呼び出す仕組みを実装。
  - PID ファイル書き込み、停止フラグ（stop_requested.flag / kill.flag）による運用制御を実装。
  - プロセス優先度設定ユーティリティ呼び出しの利用点を整備（起動直後に優先度を high に設定）。
  - ログレベル設定とバリデーション（LOG_LEVEL の許容値）を Settings 経由で提供。

### 変更 (Changed)
- .env パーサの挙動を詳細化
  - export KEY=val 形式をサポート。
  - クォート内でのバックスラッシュエスケープを解釈し、クォート閉じ以降のインラインコメントを無視する仕様を実装。
  - クォート無し値における '#' の解釈ルールを明確化（直前が空白/タブの場合にコメント扱い）。

- Execution / Order フロー
  - send_order のフローを明確化（OrderSent の永続化を broker 呼び出し前に行う設計を採用）。
  - OrderSentPendingError の扱いを定義（broker が注文番号を発行したが未約定の場合は broker_order_id を保存して OrderSent のまま残し、呼び出し元へ例外伝播）。
  - sync_order の挙動を強化（部分約定の進行で filled_qty/avg_fill_price が変化した場合は状態遷移なしでも更新する。OrderSent→Filled/PartialFill のケースは OrderAccepted を経由して遷移）。

- 環境依存の DB パス
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示。
  - execution は paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離。

- 実行時の安全性および運用
  - 起動時の kill.flag の扱いを柔軟化（KILL_FLAG_CLEAR_ON_START=1 ならクリアして起動、そうでなければ起動拒否して SystemExit）。
  - PID ファイルの書き込み場所と生成タイミングを明確化し、起動後に確実に削除するように実装。

### 修正 (Fixed)
- 発注の競合・重複に関連するクラッシュ時の不整合を軽減
  - broker 呼び出し前後での DB 更新順序を工夫し、クラッシュ後も Reconciliation により状態回復が可能になるようにした。
  - DB の一意制約違反（orders.signal_id）を DuplicateOrderError に変換して呼び出し側で扱いやすくした。

- 設定検証の堅牢化
  - validate_config による事前チェックを追加し、必須環境変数の未設定・プレースホルダ設定・KABUSYS_ENV の不正値・LOG_LEVEL の不正値等を検出してエラー/警告/情報として出力するように。
  - config/*.yaml の存在確認と（PyYAML がインストールされている場合の）パース検証を追加。PyYAML 未導入時は検証をスキップして警告出力する。

### ドキュメント（CLI ヘルプ等）
- config_setup と validate_config の CLI ヘルプを充実化（使い方、デフォルトパス、--strict 等）。
- .env を生成する際の注意（Git にコミットしない）を出力ファイルに明記。

### その他
- Risk 管理の Gate 設計（Gate1: シグナル、Gate2: 実行レート制御、Gate3: ドローダウン監視）を実装。Gate2 のレート制限は最大3回リトライとし、CIRCUIT_BREAKER 発生時の挙動を定義。
- 監視イベント（発注 latency 等）を監視 DB に記録する仕組み（モジュールとの疎結合で失敗しても発注は継続する）。

---

注: 本 CHANGELOG は提供されたコードの内容から推測して作成したものであり、実際のコミット履歴や変更差分とは異なる場合があります。実際のリリースに利用する際は Git のコミットログやリリースノートを併せてご確認ください。