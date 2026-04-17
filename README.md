# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

この README ではプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するモジュール群を提供する Python パッケージです。  
主な機能は以下の通りです：

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（実取引 / ペーパートレード切替）
- 監視（Monitoring）：プロセス・システム資源・データ鮮度・注文状態・リスクを定期的にチェック
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 補助モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針の一部：
- 本番 DB とペーパートレード用 DB は分離（KABUSYS_ENV に応じて切替）
- ルックアヘッドバイアスを避けるため日付/時刻参照に注意
- 外部 API 呼び出し（OpenAI など）は明示的に API キー管理

---

## 機能一覧（概要）

- Execution
  - 実売買 / ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory により MockBrokerClient を paper_trading 環境で利用
  - エンジンはデーモンスレッドで実行、停止フラグ検出で安全停止

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス起動状態 / データ鮮度チェック
  - TradeMonitor: 滞留注文チェック、約定価格の異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に基づき data/kill.flag を書き込み、Execution を停止させる
  - MonitoringEngine: 各 Monitor を束ねポーリング（テスト用 run_once / 本番用 run）

- Portfolio
  - 銘柄選定、等重・スコア重み付け、セクター制約、ポジションサイズ計算（単元丸め、資金制約適用）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー

- AI
  - news_nlp: raw_news を LLM（OpenAI）でスコアリングして ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを組合せて daily market_regime を判定

- ユーティリティ
  - config_setup: 対話形式で .env を生成/更新
  - validate_config: .env と config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## 必要環境 / 依存ライブラリ

主な依存（プロジェクトに requirements.txt がない場合は適宜追加してください）:
- Python 3.9+（実際の要件はプロジェクト運用方針に合わせてください）
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML（`validate_config` が YAML パースを行う場合に推奨）
- sqlite3（標準ライブラリ）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリルートで仮想環境を作成・有効化
2. 必要パッケージをインストール（上記を参照）
3. .env を作成（対話ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
   ```
5. データディレクトリ（data/）や DB ファイルは初回起動時に自動作成される場合がありますが、権限等に注意してください。

---

## 環境変数（主なもの）

必須（validate_config / Settings による）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション / デフォルト:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（production 用） デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時利用） デフォルト: data/paper_trading.db
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知に使用（任意）
- OPENAI_API_KEY: OpenAI を利用する場合に必要（news_nlp / regime_detector）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject） デフォルト: instant
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） デフォルト: 60
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（data/execution.pid 等）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（data/kill.flag 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動で .env を読み込まない（テスト用）

詳細は `src/kabusys/config.py` を参照してください。

---

## 使い方（主要コマンド）

- .env 対話ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（本番 / 開発 / paper_trading は KABUSYS_ENV に従う）
  ```
  python -m kabusys.run_execution
  ```
  注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録されます（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が既にある場合は起動しません。
  - 実行中は PID ファイル（デフォルト data/execution.pid）を出力します。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します（監視 DB は `Settings.sqlite_path`）。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムからの呼び出し）
  - ニュースセンチメント付与:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 停止・フラグファイル

- 手動停止（run_execution / run_monitoring のループを安全に抜けたい場合）:
  - プロジェクトルートの `data/stop_requested.flag` ファイルを作成すると、ループは次のポーリングで停止検出して終了します。
  - 例: `touch data/stop_requested.flag`

- KillSwitch（自動停止シグナル）:
  - Monitoring の KillSwitch が条件を満たすと `data/kill.flag` を書き込みます。
  - ExecutionEngine はこのファイルの存在を監視し、存在すると停止します（設定により自動クリアの挙動あり）。
  - 本番での自動クリアは危険なため `KILL_FLAG_CLEAR_ON_START` はデフォルト `0` を推奨。

---

## 実装上のポイント / 注意点

- Monitoring は監視ログのために常に production の sqlite_path（Settings.sqlite_path）を参照します。paper_trading であっても監視 DB は共通である点に留意してください。
- Execution の paper_trading モードではブローカー入出力がモックされ、DB は `PAPER_TRADING_SQLITE_PATH` に分離されます。
- process priority: 実行スクリプトは起動時に `set_process_priority("high")` を呼びます。プラットフォームによっては権限不足で失敗し警告が出ますが処理は継続します。
- validate_config は PyYAML 未導入時に YAML ファイルの内容検証をスキップします（警告が出ます）。
- AI 機能は OpenAI API 依存で、API レート制限・ネットワークエラーが発生し得ます。実装はリトライ・フェイルセーフ（失敗時 0 やスキップ）を組み込んでいます。

---

## 主要ディレクトリ構成

src/kabusys/ 以下の主要ファイル・モジュール（抜粋）:

- __init__.py
- config.py
- config_setup.py         — .env 対話ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  - order_record.py
  (※実行ロジック/ブローカー抽象化など)

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py
  - regime_detector.py

- data/ (実行時に生成される想定)
  - execution.pid
  - stop_requested.flag
  - kill.flag
  - monitoring.db / paper_trading.db / kabusys.duckdb など

- tools/
  - paper_verification_report.py

（各ディレクトリ内にさらに補助コード・ユーティリティが含まれます）

---

## よくある運用コマンド例

- .env を作成して検証、モニタリングとエンジンを起動する簡易ワークフロー:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  python -m kabusys.run_monitoring &   # 監視をバックグラウンドで起動
  python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 参考 / 追加情報

- コード内の docstring に設計意図・注意点が詳細に書かれています。実装を変更する際は docstring を参照してください。
- OpenAI 関連のテストでは API 呼び出し関数をモックしているので、ユニットテスト作成時はそれらを patch してテストできます。

---

問題や改善点、追加したいドキュメント項目があれば教えてください。README の補足（例: インストール用 requirements.txt の例や具体的なデプロイ手順）も作成できます。