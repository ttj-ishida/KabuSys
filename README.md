# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ、使い方、ディレクトリ構成をまとめています。開発者・運用者向けの参照ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した小規模なトレードシステムの骨格です。  
主な設計思想は次の通りです。

- シグナル駆動（DuckDB に保存されたシグナルを読み出して発注）
- ExecutionEngine（発注フロー）、OrderManager（状態管理）、RiskManager（3段階ガード）による安全性重視の発注
- 実ブラウザ（kabuステーション）／モック（テスト用）クライアントの切り替えが可能
- リコンシリエーション機能により再起動時の整合性回復を支援
- 監視プロセス（SystemMonitor）によりプロセス・リソース監視とログ収集

本リポジトリは、実運用を想定した設計を示す参考実装です。実際の運用に導入する場合は、各所の設定や外部依存の検証・テストを十分に行ってください。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検証）
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い
- ExecutionEngine（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により mock（paper_trading / development）と将来的な live を分離
- Monitoring（システム監視ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整
- ブローカー API 層
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST/WS 実装）
- 永続化（SQLite）による注文履歴管理（OrderRepository）
- DuckDB を用いたデータ分析・シグナル取得
- リスク管理（Gate 1/2/3: シグナル検査・レート制限/CB・ドローダウン監視）
- リコンシリエーション（再起動時に未確定注文を照合）

---

## 必要な環境・依存

- Python 3.10 以上を想定（| 型注釈などの記法に依存）
- 標準ライブラリ: sqlite3, threading, logging, time, pathlib, etc.
- 推奨・任意の外部パッケージ（機能に応じて必要）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証に利用。無ければ検証はスキップされ、警告が出ます）
  - defusedxml（RSS パーサなどで使用）
- インストール例:
  - pip install duckdb httpx websocket-client PyYAML defusedxml

注意: requirements.txt がリポジトリにない場合は、必要なパッケージのみ個別に入れてください。

---

## セットアップ手順

1. Python を準備（3.10+ 推奨）
2. 依存パッケージをインストール
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml
3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考にしてください（リポジトリに存在する想定）。
4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は表示されるメッセージに従い修正してください
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict
5. DB（SQLite / DuckDB）用ディレクトリを作成（通常は data/）
   - .env の DUCKDB_PATH / SQLITE_PATH に合わせ、親ディレクトリが存在するか確認してください
   - スクリプトや実行時に自動生成される場合もあります

環境変数の自動ロードについて:
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を親に検索）を起点に .env と .env.local を自動でロードします。
- OS 環境変数が優先され、.env.local は .env の上書きとして読み込まれます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト向け）。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

任意（デフォルトあり）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- LOG_LEVEL（デフォルト: INFO）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

---

## 使い方（基本コマンド）

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（Execution）
  - KABUSYS_ENV によって挙動が変わります（paper_trading → MockBrokerClient を使用して paper DB に記録）
  - 実行:
    - python -m kabusys.run_execution
- 監視プロセス（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

停止制御:
- 実行中のプロセスは data/stop_requested.flag の存在で優雅に終了します（スクリプトが参照）。
- 起動時の Kill Switch（settings.kill_flag_path、デフォルト: data/kill.flag）が存在する場合、KILL_FLAG_CLEAR_ON_START の設定により起動可否が制御されます。

ログ:
- 各プロセスは標準的な logging を使用します。LOG_LEVEL で出力レベルを制御してください。

運用時の注意:
- KABUSYS_ENV=live を設定すると本番モード想定の警告が出ます。LINE 通知設定など本番向け設定が未設定だと警告になります。
- paper_trading は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に保存されます。

---

## ディレクトリ構成（主要ファイル説明）

リポジトリ内の主要なソース配置（src/kabusys を起点に抜粋）

- src/kabusys/__init__.py
  - パッケージ定義・バージョン情報

- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス
  - .env / .env.local 自動ロードロジック
  - 必須チェックのユーティリティ

- src/kabusys/config_setup.py
  - .env を対話式で作成・更新するウィザード

- src/kabusys/validate_config.py
  - 起動前に .env / config/*.yaml の妥当性を検査する CLI

- src/kabusys/run_execution.py
  - ExecutionEngine 起動用スクリプト（プロセス優先度設定、DB 接続、PID/停止フラグ管理）

- src/kabusys/run_monitoring.py
  - SystemMonitor 起動用スクリプト（ポーリングループ）

- src/kabusys/execution/
  - broker_api.py
    - BrokerAPI のデータモデル、Protocol、例外、ファクトリ
  - kabu_client.py
    - kabuステーション REST/WebSocket 実装（KabuStationClient）
  - mock_client.py
    - MockBrokerClient（テスト用）
  - broker_factory.py
    - Settings に基づきブローカークライアントを生成
  - order_record.py
    - OrderRecord（状態遷移ロジック）
  - order_repository.py
    - SQLite による永続化（orders テーブル定義、CRUD）
  - order_manager.py
    - OrderManager（OrderRecord + OrderRepository を組み合わせた発注フロー）
  - execution_engine.py
    - ExecutionEngine（シグナル処理ループ、push ドレイン）
  - reconciler.py
    - 再起動時の OrderSent 照合とポジション差分照合
  - risk_manager.py
    - 3段階ガード（Gate 1/2/3）

- src/kabusys/data/
  - calendar_management.py
    - JPX カレンダー管理（DuckDB + J-Quants 連携の想定）
  - news_collector.py
    - RSS ニュース収集（正規化・SSRF 対策・保存ロジック）

- src/kabusys/monitoring/
  - monitoring_db.py
    - 監視用 SQLite テーブルの初期化・書き込みユーティリティ
  - system_monitor.py
    - システムリソース・稼働監視ロジック（起動状況、リソース閾値）

- src/kabusys/utils/
  - logging_setup.py
    - ロギング初期化ユーティリティ
  - process_priority.py
    - プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - validate_config.py が存在をチェック。生成スクリプト（python scripts/generate_config.py）に触れるログメッセージあり（リポジトリに存在する場合はそちらを使って生成）。

- data/
  - 実行時に使用する SQLite / DuckDB / PID / flag 等を格納する想定のディレクトリ（デフォルトパスは .env で制御）

---

## 追加メモ（設計上の重要点）

- 発注フローはクラッシュ安全性を考慮した2相永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted 更新）設計になっています。リコンシリエーションで不整合を回復できるようにしています。
- MockBrokerClient は paper_trading / development のテスト用に豊富な挙動（instant / partial / never / reject）を備えています。
- RiskManager は三段階の防御を提供し、レート制限やサーキットブレーカー、ドローダウン監視を実装しています。
- カレンダー・ニュース収集等の data 側は DuckDB を想定し、J-Quants API からのデータ取得に基づく設計になっています（J-Quants トークンは JQUANTS_REFRESH_TOKEN）。

---

もし README に追加してほしい内容（例: 具体的な .env.example、CI 実行方法、実運用チェックリスト、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記します。