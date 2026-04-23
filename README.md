# KabuSys

日本株自動売買システムの軽量コアライブラリ（リファクタ／教育用）。  
このリポジトリは、発注エンジン・リスクガード・モニタリング・データ収集等の主要コンポーネントを備えています。実運用向けの設計（Kill Switch、Reconciliation、Circuit Breaker 等）を取り入れつつ、ローカルでのペーパートレードや単体テストが可能なモック実装も提供します。

## 主な特徴
- 環境設定ウィザード（.env を対話式で生成／更新）
- 起動前の設定検証ツール（環境変数・config/*.yaml の存在／パース確認）
- ExecutionEngine：シグナルプル型の発注エンジン（シグナル処理 + push ドレイン）
- Broker クライアント抽象化（実ブローカー／MockBroker の切り替え）
- Order のステートマシンと永続化（SQLite）
- 起動時のリコンシリエーション（OrderSent の同期、ポジション差分検出）
- RiskManager：Gate1〜3 の三段階リスクガード（余力、レート制限、ドローダウン）
- SystemMonitor：監視ループ実装（SQLite / DuckDB 使用）
- データ処理モジュール（マーケットカレンダー、ニュース収集等）

## 重要なスクリプト／エントリポイント
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視ループ起動: python -m kabusys.run_monitoring
- 発注エンジン起動: python -m kabusys.run_execution

## 必要な依存ライブラリ（代表例）
リポジトリに requirements.txt がない場合、少なくとも以下が必要になります（機能により増減します）：
- python >= 3.8+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config.yaml のパース検証を行う場合）
- その他：標準ライブラリの sqlite3 等

インストール例:
```
python -m pip install duckdb httpx websocket-client defusedxml pyyaml
```

※ 実際のプロジェクトでは requirements.txt / poetry / pipenv 等で依存を管理してください。

## セットアップ手順（ローカル実行向け）
1. リポジトリをクローンし、Python 仮想環境を作成してアクティベートします。
2. 依存パッケージをインストールします（上記参照）。
3. .env を作成（対話式推奨）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに従って必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定してください。

4. 設定検証を実行して問題ないか確認:
   ```
   python -m kabusys.validate_config
   ```
   警告もエラー扱いにする strict モード:
   ```
   python -m kabusys.validate_config --strict
   ```

5. DB ディレクトリ（デフォルト: data/）や必要なファイルが存在するか確認。多くのケースで起動時に親ディレクトリが自動作成されますが、権限等に注意してください。

## 環境変数（主要）
設定は OS 環境変数、またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（Settings クラスで自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（代表）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（live 環境で推奨）

その他の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_*、閾値系など）は Settings クラスのプロパティを参照してください。

## 使い方（主要フロー）
1. .env 作成:
   - 上記の config_setup ウィザードで作成できます。ウィザードは既存 .env を読み込んで編集可能です。

2. 設定検証:
   - validate_config は必須 env の未設定、プレースホルダ値、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）をチェックします。
   - 例: `python -m kabusys.validate_config --strict`

3. 監視（SystemMonitor）起動:
   - デーモン的に監視を回すスクリプト。
   - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で秒数を指定（デフォルト 60）。
   - 例: `python -m kabusys.run_monitoring`

4. 実際の発注エンジン起動:
   - ExecutionEngine を起動します。KABUSYS_ENV によって MockBroker（development / paper_trading）か Live ブローカーを選択します（現状 Live は未実装で NotImplementedError を出す実装になっています）。
   - `data/stop_requested.flag` が存在すると起動しない / 停止する仕組み。
   - PID ファイルや Kill Flag の扱いに注意してください。
   - 例: `python -m kabusys.run_execution`

5. テスト・開発:
   - KABUSYS_ENV=development / paper_trading では MockBrokerClient が使用され、実際の kabu station を必要とせずローカルで動作確認が可能です。
   - MockBrokerClient は fill_mode（instant/partial/never/reject）で挙動を切り替えできます（PAPER_FILL_MODE）。

## ファイル／ディレクトリ構成（抜粋）
src/kabusys 以下の主要ファイルを示します（プロジェクトルートは src/ の親）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込みと Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_monitoring.py         — 監視ループ起動スクリプト
  - run_execution.py          — 発注エンジン起動スクリプト

  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集（raw_news 保存等）
    - jquants_client.py       —（参照される想定の J-Quants クライアント）

  - execution/
    - broker_api.py           — Broker API のデータモデル／Protocol／ファクトリ
    - broker_factory.py       — Settings に基づきブローカー client を生成
    - kabu_client.py          — kabu station 実クライアント（httpx / websocket）
    - mock_client.py          — テスト用モック broker
    - order_record.py         — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py     — SQLite 永続化層（orders テーブル）
    - order_manager.py        — 外向け API（作成／送信／同期／キャンセル）
    - execution_engine.py     — セッション実行ロジック（シグナル処理／push ドレイン）
    - reconciler.py           — 起動時リコンシリエーション（OrderSent 同期）
    - risk_manager.py         — Gate1〜3 のリスクガード

  - monitoring/
    - monitoring_db.py        — 監視DB 初期化とログ保存
    - system_monitor.py       — システム資源監視など（CPU/MEM/DISK 閾値）

  - utils/
    - logging_setup.py        — ロギングの初期化ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, ... （期待される設定ファイルの例）

- data/
  - (デフォルトの DB / PID / flag ファイルはここに置かれる。例: data/kabusys.duckdb, data/monitoring.db, data/execution.pid, data/kill.flag)

## 実装上の注意点
- Settings はプロジェクトルートを .git または pyproject.toml を起点に自動検出し、.env / .env.local を優先順で読み込みます。OS 環境変数は保護され、.env.local の override は可能ですが OS の既存変数は上書きされません。
- Order の永続化は SQLite で行われ、`orders` テーブルには active 注文の signal_id の一意制約（部分ユニーク）があります（衝突を DB レベルで防止）。
- ExecutionEngine はセッション時間（デフォルト: シグナル処理 8:50-9:10、市場クローズ 15:30）を想定した実行フローを持ちます。テスト時は個別メソッドを直接呼ぶことが推奨されます。
- Live ブローカーの実装（KabuStationClient を実際に運用する場合）ではネットワーク・認証・レート制限・エラー処理に注意してください（KabuStationClient の _request メソッド参照）。

## トラブルシューティング
- validate_config のエラーに従い必須環境変数を設定してください。警告は --strict で失敗扱いにできます。
- 起動時に kill.flag（デフォルト data/kill.flag）があるとエンジンは起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 を .env で設定すると起動時に自動クリアできますが、本番では推奨されません。
- SQLite/DuckDB のパスに対して親ディレクトリが存在しない場合、警告が出ます。通常は起動時にディレクトリを作成するコードがありますが、パーミッションに注意してください。
- Live environment を本当に利用する場合、LINE や監視の設定（LINE_CHANNEL_ACCESS_TOKEN 等）を確認してください。

---

この README はコードベースの主要な機能・起動手順・構成をまとめた概要ドキュメントです。実運用や詳細な導入手順、CI/CD、テスト戦略等は別ドキュメント（CONTRIBUTING.md、DEPLOYMENT.md 等）で補完することを推奨します。必要であれば README の追補版（環境ごとのセットアップ例、Docker 化、systemd サービス定義 など）を作成します。