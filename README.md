# KabuSys

日本株向け自動売買システムのコア実装（ライブラリ／実行スクリプト群）

このリポジトリは、kabuステーション（またはモック）を用いた発注エンジン、リスクガード、監視・リコンシリエーション、データ基盤周り（カレンダー・ニュース収集）など、自動売買システムの主要コンポーネントを提供します。

---

## 概要

主な設計方針・特徴：

- 発注フローはクラッシュ耐性を意識した二相永続化方式（OrderCreated→OrderSent の永続化、broker_order_id の永続化等）を採用。
- 3段階リスクガード（Gate1: シグナルレベル、Gate2: エグゼキューション／レート制限・サーキットブレーカー、Gate3: ドローダウン監視）。
- 起動時のリコンシリエーション（OrderSent の突合）でクラッシュ後の自動復旧を支援。
- 開発／テスト用途に MockBrokerClient を用意。paper_trading 環境ではモックを使って本番データと分離。
- .env ウィザード・設定検証ツールを同梱。YAML 設定の存在・パースチェック（PyYAML 必須）をサポート。
- DuckDB（分析用）と SQLite（監視/発注永続化）を使用。

---

## 主な機能一覧

- 環境設定管理
  - 自動 .env ロード（プロジェクトルートを .git / pyproject.toml で検出）
  - 対話式ウィザードで .env を生成/更新（kabusys.config_setup）
  - 設定検証 CLI（必須環境変数、config/*.yaml、本番ガード等のチェック） — kabusys.validate_config

- 発注（Execution）
  - ExecutionEngine（シグナル取得 → リスクチェック → 発注 → WebSocket push ドレイン）
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（外向け API：create/send/sync/cancel）
  - Broker クライアント群
    - KabuStationClient（kabuステーション REST API 実装）
    - MockBrokerClient（テスト用モック）
    - broker_factory（設定に応じてクライアントを生成）
  - Reconciler（起動時の OrderSent 突合、ポジション差分検出）
  - RiskManager（Gate1/2/3 を実装）

- 監視（Monitoring）
  - run_monitoring スクリプト（SystemMonitor をポーリング、MONITOR_POLL_INTERVAL で間隔制御）

- データ
  - カレンダー管理（JPX カレンダー、next_trading_day / get_trading_days 等）
  - ニュース収集（RSS 収集・前処理・DB 保存ロジック）

---

## 動作要件（推奨）

- Python 3.10+
  - 型アノテーション（X | Y）を使用しているため Python 3.10 以上を推奨します。
- 必要な Python パッケージ（例）
  - httpx
  - websocket-client
  - duckdb
  - defusedxml
  - PyYAML（config/*.yaml のパース検証を行う場合）
- SQLite（Python 標準ライブラリに含まれます）
- kabuステーション（本番接続を行う場合）

pip によるインストール例（requirements.txt がない場合の例）:
```bash
pip install httpx websocket-client duckdb defusedxml PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. Python 環境を作成・有効化（推奨: venv / pyenv）。

3. 必要パッケージをインストール（上記を参照）。

4. プロジェクトルートに .env を配置する（対話式ウィザード推奨）。

- 対話式で .env を作る:
  ```bash
  python -m kabusys.config_setup
  ```
  これにより .env（デフォルト）を生成できます。--env-file 引数でパスを指定可能。

- 既存の .env を編集する場合は .env.local を使って上書きも可能。

5. 設定検証（起動前に必ず実行推奨）:
  ```bash
  python -m kabusys.validate_config
  # 警告も FAIL 扱いにする場合
  python -m kabusys.validate_config --strict
  ```

6. データディレクトリを作成（必要に応じて）:
  - デフォルトの DB パス: data/kabusys.duckdb, data/monitoring.db
  ```bash
  mkdir -p data
  ```

---

## 主要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（主要なもの）:
- KABUSYS_ENV — 実行モード: development / paper_trading / live（live は注意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL — kabuステーションの base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知

その他:
- PAPER_FILL_MODE — paper_trading の mock fill 動作（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 起動制御・監視関連
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

サンプル .env（簡易）:
```
KABUSYS_ENV=paper_trading
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant
```

注意:
- .env は絶対にレポジトリにコミットしないでください（config_setup でも注意喚起あり）。

---

## 使い方（起動例）

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  ```

- 発注（ExecutionEngine）起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により MockBroker（paper_trading / development）か Live ブローカーかの選択を行います。
  - 現状 Live ブローカーは未実装の箇所がある旨（BrokerClientFactory が NotImplementedError を投げる）ため、開発・検証は paper_trading / development を推奨。

- 停止制御
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を検知して終了します（停止要求ファイル）。
  - 起動抑止用の kill.flag（settings.kill_flag_path）を利用して起動を阻止できます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（注意: 本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

  - execution/
    - __init__.py
    - broker_api.py              — Broker API データモデル・Protocol・ファクトリ
    - kabu_client.py             — kabu station 実装（httpx）
    - mock_client.py             — モックブローカー（テスト用）
    - broker_factory.py          — Settings に基づくクライアント生成
    - execution_engine.py        — ExecutionEngine（シグナル処理 / push ドレイン）
    - order_record.py            — Order 状態遷移モデル
    - order_repository.py        — SQLite 永続化
    - order_manager.py           — 発注フロー制御（create/send/sync/cancel）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — Gate1/2/3 のリスクガード

  - data/
    - calendar_management.py     — JPX カレンダー管理（next_trading_day 等）
    - news_collector.py          — RSS ニュース収集・前処理

  - monitoring/                  — 監視関連（監視DB 初期化等）※本READMEでは詳細省略
  - utils/                       — ロギング設定・プロセス優先度などのユーティリティ（参照される）

---

## 注意点 / 運用上のポイント

- 本番（KABUSYS_ENV=live）モードは慎重に使用してください。validate_config は live 時に追加警告を出します（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）。
- 発注フローはクラッシュ時に OrderSent のまま残るケースを考慮しています。起動時の Reconciler が重要です。定期的にリコンシリエーションを行う運用を推奨します。
- Paper trading（モック）と本番 DB は分離されます（paper_trading 用 SQLite パスを利用）。運用ミスで本番 DB を上書きしないように注意してください。
- config/*.yaml の存在・パースは PyYAML のインストール有無に依存します。検証をフルに行うには PyYAML を入れてください。
- ローカルテストでは MockBrokerClient を使うと kabuステーション無しで動作確認できます（PAPER_FILL_MODE の制御で拒否／部分約定／即時約定をシミュレート可能）。

---

## 今後の拡張案（参考）

- Live ブローカークライアントの堅牢化（実装／テスト）
- Web UI や簡易ダッシュボードによる監視・アラート表示
- バックテスト・最適化用の追加ツール群
- モジュール化されたプラグイン式ストラテジー導入

---

README の内容やセットアップ手順で不明点があれば、どの機能（例: Execution 起動、Reconciler、calendar_update_job、news_collector の動作など）について詳しく知りたいか教えてください。