# KabuSys

日本株自動売買システムの軽量コアライブラリ群です。本リポジトリは戦略・ポートフォリオ構築・注文実行・監視・解析ツールおよび AI 補助モジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下用途を想定したモジュール群を提供します。

- データ解析 / ファクター計算（DuckDB 上の時系列データ参照）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 注文実行エンジン（本番 / ペーパートレード分離）
- 監視 / アラート（システム状態・注文・リスク監視、Kill Switch）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、環境設定ウィザード、設定検証）
- レポート / ツール（ペーパートレード検証レポート等）

設計方針の概略:
- 本番 DB とペーパートレード DB を分離（ペーパートレードは `KABUSYS_ENV=paper_trading` を利用）
- 主要処理は外部 API によらずローカル DB（DuckDB/SQLite）参照で実行可能
- OpenAI を使う機能は API キーが必要で、フォールバック / エラー処理を持つ

---

## 主な機能一覧

- 環境設定ウィザード: `kabusys.config_setup`（.env の対話式作成）
- 設定検証 CLI: `kabusys.validate_config`（.env / config/*.yaml 検証）
- 実行エンジン起動: `kabusys.run_execution`（ExecutionEngine 起動、ペーパートレード切替）
- 監視ループ起動: `kabusys.run_monitoring`（System/Trade/Risk Monitor をポーリング）
- Paper Trading レポート: `kabusys.tools.paper_verification_report`
- AI:
  - ニュース NLP スコアリング: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
- ポートフォリオ構築ユーティリティ:
  - 候補選定 / 重み計算 / 株数算出 / セクター上限 / レジーム乗数
- ログ設定ユーティリティ: 統一的な stdout + 日次ローテーションログ
- プロセス優先度設定（Windows / POSIX 向けラッパー）

---

## セットアップ手順（ローカル開発向け）

推奨: Python 仮想環境を使用してください。

1. リポジトリをクローンし、作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存ライブラリをインストール
   - 本リポジトリには requirements.txt が付属していない想定のため、少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（`validate_config` が YAML ファイルの検証を行う場合に推奨）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはルート直下に `.env` を作成して下記の必須項目を設定してください。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗と扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

重要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 主要:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - OPENAI_API_KEY — OpenAI を使う機能に必要
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — デフォルト: logs/
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、default 0 推奨）

（`kabusys/config.py` と `validate_config.py` に詳細が実装されています）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を生成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動（注文実行）
  - 本番/開発/ペーパーは KABUSYS_ENV に依存します。
  - ペーパートレード時は `KABUSYS_ENV=paper_trading` を設定すると MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH` に記録されます。
  ```
  python -m kabusys.run_execution
  ```
  実行時:
  - プロセス優先度を "high" に設定します（可能な限り）。
  - `data/stop_requested.flag` が存在すると起動しない / 実行中に検知すると停止します。
  - PID ファイル: `data/execution.pid`（デフォルト）

- 監視ループ起動
  - 監視は常に `Settings.sqlite_path`（production sqlite path）を使用します（`run_monitoring.py` の仕様）。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に変更可能（デフォルト 60 秒）。
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB 指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼ぶ）
  - ニュース NLP スコアリング:
    - 関数: `kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)`
    - `api_key` を渡すか環境変数 `OPENAI_API_KEY` を設定してください。
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)`

---

## 運用上の注意・安全策

- 本番環境（KABUSYS_ENV=live）では必須設定や LINE の通知設定を慎重に確認してください。`validate_config` は live 環境時に追加警告を出します。
- `KILL_FLAG`（data/kill.flag）:
  - Kill Switch は `KillSwitch` により `data/kill.flag` を書き込むことで ExecutionEngine 停止をトリガーします。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険（自動クリアされるため）なので推奨しません。
- `stop_requested.flag`（data/stop_requested.flag）:
  - 起動スクリプトはこのファイルの存在をチェックし、あれば起動を中止または実行中に停止します。
- ログ出力:
  - デフォルトは `logs/<app_name>.log` （日次ローテーション、30日保持）。`LOG_DIR` で変更可能。
  - ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。
- Process Priority / CPU affinity:
  - `psutil` による操作で権限が必要になる場合があります。`AccessDenied` 等は警告となり処理は継続します。

---

## ディレクトリ構成（主要ファイル）

ルート: `src/kabusys/` を想定。主要モジュールを抜粋して示します。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/                 — ExecutionEngine / BrokerFactory / OrderManager 等（補助モジュール）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                      — デフォルトの DB／フラグ保存場所（`data/monitoring.db`, `data/kabusys.duckdb`, `data/paper_trading.db`）

（実際のレポジトリ内にある各サブモジュールを参照してください）

---

## 重要な実装詳細（補足）

- run_monitoring.py
  - 監視は常に `settings.sqlite_path`（監視 DB）を使用します。`MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（1 秒以上）。デフォルト 60 秒。
- run_execution.py
  - `KABUSYS_ENV=paper_trading` の場合、Mock Broker を使い `paper_sqlite_path`（既定: `data/paper_trading.db`）に記録します。本番 DB と完全分離。
  - 実行中、`data/stop_requested.flag` による停止監視を行います。PID は `data/execution.pid` に書き込まれます。
- monitoring_db (SQLite)
  - `init_monitoring_db` は冪等でテーブルとインデックスを作成し、必要に応じて簡単なマイグレーション（カラム追加）を行います。
- AI モジュール
  - `OPENAI_API_KEY` を必要とします。レスポンスの堅牢性確保（JSON 検証、リトライ、スコアクリップ）を行っています。

---

## トラブルシューティング

- ログファイルが作成されない:
  - `LOG_DIR` の親ディレクトリの書き込み権限を確認してください。作成に失敗するとコンソール出力のみになります。
- psutil 関連の警告（優先度設定失敗）:
  - 権限不足の場合があります。警告は出ますが処理自体は継続されます。
- OpenAI API 呼び出しの失敗:
  - `OPENAI_API_KEY` が有効か確認。ネットワークやレート制限によりリトライする実装がありますが、最終的にスキップされることがあります。
- DB マイグレーション:
  - `monitoring_db.init_monitoring_db` は起動時に必要テーブルとカラムを作成します。古い DB を再利用する場合はスキーマ整合性に注意してください。

---

## 開発メモ / 拡張ポイント

- position sizing の lot_size を銘柄別に拡張する（現状は一律 100）
- AI モデルやプロンプトの追加チューニング
- order_manager / broker_client のモックを充実させて単体テストを拡張
- DuckDB クエリの高速化・インデックス設計
- より詳細な運用ドキュメント（systemd / cron 起動例、監視アラート設定）

---

以上が本リポジトリの README です。追加で README に入れたい実行例や CI・デプロイ手順等があれば教えてください。