Keep a Changelog
=================

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠します。
このプロジェクトのバージョン管理方針に従い、主要な変更は以下にまとめられています。

注意
----
この CHANGELOG は現在のコードベース（src/ 以下の実装）から機能・動作を推測して作成した初期リリース向けの要約です。

Unreleased
----------
- なし

[0.1.0] - 2026-04-22
--------------------
Added
- 初期公開リリース: バージョン情報は `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。
- 環境設定 / 管理
  - 自動 .env ロード機能を実装（OS 環境変数優先、.env → .env.local の順で読み込み）。無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - `.env` のパース処理を強化（`export KEY=val` 形式対応、クォート文字内のバックスラッシュエスケープ対応、インラインコメント処理）。
  - `_load_env_file` にて既存環境を保護する "protected" 機構を導入（OS 環境変数を上書きしない）。
  - `Settings` クラスによる環境変数ラッパーを実装（必須値チェック `_require`、各種パス・閾値・モードのプロパティを提供）。
  - Paper trading 向けに DB を分離する設定（`paper_sqlite_path`、`paper_fill_mode`）。
- 対話式ウィザード CLI
  - `src/kabusys/config_setup.py` に .env の初期作成/更新用ウィザードを実装。シークレット項目はマスク表示、選択肢・デフォルト値をサポート、保存前確認を実装。
  - `.env` の書き出しフォーマットを定義（ヘッダ・セクション付き）。
- 設定検証 CLI
  - `src/kabusys/validate_config.py` に起動前検証ツールを追加。必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL 値検証、DB パス親ディレクトリ確認、config/*.yaml の存在確認および（PyYAML 有無に応じた）パース検証を実施。
  - `--strict` オプションで警告も失敗扱いにできる。
- 実行用エントリスクリプト
  - `src/kabusys/run_execution.py` に ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、PID 管理、stop フラグ検出、paper_trading の DB 分離をサポート。
  - `src/kabusys/run_monitoring.py` に SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数で間隔上書き、監視は環境に関係なく本番 sqlite_path を使用。
- 発注エンジンと注文管理
  - `ExecutionEngine`（`src/kabusys/execution/execution_engine.py`）を実装。シグナル処理（8:50–9:10）と WebSocket push ドレイン（9:10–15:30）を備え、リコンシリエーション実行、kill.flag による起動拒否/自動クリア（`KILL_FLAG_CLEAR_ON_START`）を実装。
  - `OrderRecord`（`src/kabusys/execution/order_record.py`）に状態機械（OrderState）と遷移検証を実装。許可されない遷移は `InvalidStateTransitionError` を raise。
  - `OrderManager`（`src/kabusys/execution/order_manager.py`）に create/send/sync/cancel の高レベル API を実装。重複注文検出（`DuplicateOrderError`）、2 相永続化（OrderSent 前後の永続化設計）の説明、`OrderSentPendingError` の扱い、broker 状態同期ロジックを導入。
  - リスクゲート（Gate1/2/3）を組み込んだ発注フロー（レート制限・サーキットブレーカー・ドローダウンチェック）、発注成功時の position_entries への書き込みを実装（DuckDB を用いたポートフォリオ管理）。
  - kill_switch による全 active 注文のキャンセル処理を実装。キャンセル時の例外処理とログ出力を考慮。
- ブローカークライアント（kabu）
  - `KabuStationClient`（`src/kabusys/execution/kabu_client.py`）を実装。httpx による同期 REST 呼び出し、トークン取得の遅延初期化と 401 時の再取得リトライ、429 をレート制限エラーとして扱うなどのエラーハンドリングを実装。
  - kabu ステータスコード→内部ステータス（open/partial/filled/cancelled/rejected）マッピングを提供。
  - WebSocket push（stream_push）に対応する設計（on_message コールバックで _push_queue に投入する仕組み）を導入。
- 永続化 / 監視
  - DuckDB と SQLite（監視 DB）を併用。監視用 DB 初期化ユーティリティ `init_monitoring_db` の利用を想定。
  - 監視ログ（発注イベントやレイテンシ）を監視 DB に記録するフックを追加。
- ログ・プロセス優先度
  - `setup_logging` と `set_process_priority` の呼び出しを各スクリプト先頭に配置していることを想定（ログ初期化と高優先度プロセス設定）。

Changed
- 初回リリースのため該当なし（すべて新規実装）。

Fixed
- 初回リリースのため該当なし。

Security
- .env ファイルの取り扱いに関する注意を明記（`config_setup.py` の出力ヘッダに「.env は絶対に Git にコミットしないこと」を記載）。
- シークレット情報はウィザード表示でマスクされる設計（ただしファイル自体はローカル保存されるため運用での保護を推奨）。

Notes / 実装上の注意点（要確認）
- `validate_config` は PyYAML が未インストール時に YAML 内容検証をスキップし、警告を出す。
- `Settings` のプロパティは不正値で例外を投げるため、起動前に `validate_config` でチェックすることを推奨。
- ExecutionEngine の run_session は PID ファイル管理と kill.flag の状態に依存するため、運用時のファイルパス権限・存在確認が必要。
- `KabuStationClient` は httpx.Client を使用しており、async 実装への移行が将来的に可能（httpx.AsyncClient へ切替え）。

今後の予定（例）
- 単体テストの整備（OrderManager / ExecutionEngine の主要フロー）
- より詳細なリコンシリエーションレポート出力
- WebSocket/Async 対応の追加実装
- デプロイ向けの設定テンプレート（.env.example の整備）

以上。必要であれば各ファイルごとの差分や設計図（ER 図、状態遷移図、起動フロー）を追記します。どの粒度で追記しますか？