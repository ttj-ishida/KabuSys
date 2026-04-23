Keep a Changelog
=================

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠します。

※ ここに記載した内容はコードベース（src/ 以下）から推測してまとめた初期リリースの変更履歴です。

[Unreleased]
------------

- 現時点の開発中の変更はありません。

0.1.0 - 2026-04-23
-----------------

Added
- 初期リリース。
- 設定/環境関連:
  - Settings クラスを導入し、環境変数をラップしてプロパティ経由でアクセス可能に（src/kabusys/config.py）。
  - .env 自動読み込み機構を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - .env パーサーの実装: export プレフィックス、引用符（シングル/ダブル）、エスケープ、およびインラインコメント処理に対応。
  - PAPER_FILL_MODE の値検証や各種パス/閾値設定のプロパティを提供。
- 設定ウィザード:
  - 対話式 .env 作成/更新ウィザードを追加（src/kabusys/config_setup.py）。標準項目（J-Quants、kabuステーション、DB パス、LINE、ログレベル、Kill Flag 設定等）をサポートし、.env を書き出す機能を提供。
- 設定検証 CLI:
  - validate_config CLI を追加（src/kabusys/validate_config.py）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告も失敗扱いにできる。
- 実行エントリポイント:
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。paper_trading モードで専用 SQLite を使用する分離動作、プロセス優先度設定、PID/停止フラグ管理を実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能、監視用 DB の初期化とポーリングループを提供。
- 発注ロジック／実行基盤:
  - OrderRecord（状態遷移モデル）を実装（src/kabusys/execution/order_record.py）。状態列挙(OrderState)、許可遷移テーブル、遷移検証とタイムスタンプ更新を提供。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。create/send/sync/cancel の高レベル API、DuplicateOrderError、2相永続化（OrderSent 前に DB 更新してから broker 呼び出し）や OrderSentPendingError の扱い、sync の詳細ロジックを提供。
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。シグナル読み込み → Gate1/Gate2 リスクチェック → 発注フロー、WebSocket push ドレイン、Gate3（ドローダウン監視）と kill_switch、セッション制御（時刻ベース）、リコンシリエーション呼び出しなどのフローを実装。
  - run_session の PID 管理／kill.flag の起動時動作（KILL_FLAG_CLEAR_ON_START の扱い）を実装。
  - 発注フロー内での position_entries への記録（buy/sell の扱い）やモニタリング DB へのイベント記録フックを追加。
- broker クライアント:
  - KabuStationClient を追加（src/kabusys/execution/kabu_client.py）。httpx を利用した同期 REST クライアント、トークン取得・自動再取得、401 リトライ、429（RateLimit）および 5xx エラーのハンドリング、JSON パースの例外変換、kabu ステータスコード → 内部状態マッピング、WebSocket push 受信（stream_push を想定）を実装。
- その他ユーティリティ連携:
  - logging/setup や process_priority ユーティリティを利用してプロセス優先度設定とロギング初期化を行うコードを導入（run_execution/run_monitoring 等）。
  - monitoring_db の初期化フックを導入（監視用 SQLite のテーブル作成を保証）。

Changed
- 初回公開のため特定の変更履歴はなし（新規実装中心）。

Fixed
- 初回公開のため特定の修正履歴はなし。

Removed
- なし。

Security
- .env は絶対に Git にコミットしないよう注意書きを追加（config_setup が生成する .env ヘッダ内に明記）。

Notes / 動作上の注意
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ有効。未インストール時はパース検証をスキップして警告を出す。
- Settings は環境変数の妥当性チェック（一部はプロパティで ValueError を投げる）を行うため、外部からの設定ミスがあると例外で早期検出される。
- ExecutionEngine / OrderManager は多段の例外・クラッシュ耐性設計を盛り込んでいる（OrderSent の永続化タイミングや OrderSentPending の扱い、Reconciliation を通じた復旧など）。
- run_monitoring は常に本番用の sqlite_path を使用する設計（KABUSYS_ENV に依存せず本番 DB を参照する点に注意）。

開発者向け
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py に記載）
- 今後のリリースでは、テストカバレッジ、エンドツーエンドのリコンシリエーションケース、および async 対応（httpx.AsyncClient）を検討。

---