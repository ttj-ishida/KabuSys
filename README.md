# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト）です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注（本番／ペーパートレード）・監視・リサーチ・AI を組み合わせたモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を持つモジュール群で構成されています:

- 発注エンジン（ExecutionEngine）: 実際のブローカー連携またはモック（ペーパートレード）で注文を管理
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェックし、Kill Switch による停止を行う
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ決定・セクター制約適用
- リサーチ: DuckDB を使ったファクター計算・特徴量探索
- AI モジュール: OpenAI を利用したニュースセンチメントや市場レジーム判定
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等
- ツール: ペーパートレード検証レポート生成スクリプトなど

設計のポイント:
- 環境変数 / .env による設定管理
- DuckDB（分析）と SQLite（監視 / 注文履歴）を併用
- 本番 DB とペーパートレード DB を分離
- ログは stdout と日次ローテーションファイルに出力
- AI 機能は OpenAI キーが必要。失敗時はフェイルセーフで継続

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパー切替）
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションあり）
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringDB
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research: ファクター計算（momentum/value/volatility）、IC 計算、統計サマリー
- ai: ニュース NLP（score_news）、市場レジーム判定（score_regime）
- tools: paper_verification_report（ペーパートレード検証レポート生成）

---

## 依存関係（代表）

最低動作には Python 3.10+ を推奨します（型ヒントや union 型表記により）。  
主な外部ライブラリ:

- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config YAML 検証を行う場合）
- その他（標準ライブラリ: sqlite3, logging など）

requirements.txt がある場合は次でインストールしてください:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

必要に応じて個別インストール:

```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール（上の例参照）

3. .env 作成（対話ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuAPI パスワードなどの必須項目を対話的に設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主なオプション/デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（等）
     - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 厳密モード（警告も FAIL とする）
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ / ログディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` と `logs/` にファイルを作成します。自動生成される場合もありますが、事前に作成しておくと権限問題を回避できます。

---

## 使い方

### 実行（ExecutionEngine）

- 本番 / ペーパートレードは KABUSYS_ENV で切り替えます。

ペーパートレード起動例:
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

本番（live）起動例:
```bash
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

挙動:
- paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
- エンジンは data/execution.pid（デフォルト）に PID を書きます。
- 停止は data/stop_requested.flag を作成することで行えます（監視プロセス・エンジンはいずれもこれを検出して安全に停止します）。

### 監視（Monitoring）

起動例:
```bash
python -m kabusys.run_monitoring
```

- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に上書き可能（デフォルト 60 秒）。
- 監視は Settings にかかわらず本番 sqlite_path を使用して監視 DB にログを残します（monitoring は常に本番 DB を監視する前提）。
- 停止フラグ: data/stop_requested.flag を作成するとループを終了します。

### ログ設定

- ログは stdout（コンソール）と日次ローテーションファイル（logs/<app_name>.log）で出力されます。
- LOG_LEVEL と LOG_DIR 環境変数で上書き可能。
- setup_logging(app_name="execution") などで統一設定を使用します。

### 設定検証

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- .env の必須項目や config/*.yaml の存在・パースをチェックします（PyYAML が無い場合は YAML 検証をスキップします）。

### .env の自動ロード

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索し `.env` と `.env.local` を自動で読み込みます。自動ロードを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

### AI 機能（OpenAI）

- ニュースのセンチメント解析やレジーム判定は OpenAI API を使用します。環境変数 `OPENAI_API_KEY` を設定するか、API キーを関数に渡してください。
- 例（プログラム的に呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

### ペーパートレード検証レポート

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db オプションで DB パスを指定可能
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを表示し PASS/FAIL 判定を行います。

---

## 重要なファイル・フラグ

- data/kill.flag : Kill Switch により ExecutionEngine を停止させるためのフラグ（KillSwitch が書き込む）
- data/stop_requested.flag : ローカル制御用の停止フラグ。run_execution/run_monitoring が検出して終了
- data/execution.pid : ExecutionEngine の PID ファイル（デフォルト）
- ログ: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）

KILL_FLAG_CLEAR_ON_START=1 の設定は本番では危険です（自動で Kill Flag をクリアするため）。本番環境では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なツリーは次の通り（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py など)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/                    — (データ・DB ファイルの配置先。実行時に利用)

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/デフォルト:
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を利用する場合に必須（AI 機能）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）

詳細は `src/kabusys/config.py` と `src/kabusys/config_setup.py` の定義を参照してください。

---

## 開発時の注意点 / 補足

- DuckDB 接続は解析用途に使用し、prices_daily / raw_financials / raw_news などのテーブルを参照します。
- 重要な操作（AI 呼び出し・DB 書き込みなど）はフェイルセーフを意識して実装されていますが、本番での運用前には十分な検証（validate_config の確認、ペーパートレードでの検証）を行ってください。
- OS 権限により psutil を利用したプロセス優先度や CPU affinity の設定が失敗する場合があります。失敗時はログに警告が出ますが処理は継続します。
- `.env` は絶対に Git にコミットしないでください（config_setup でも警告されています）。

---

必要であれば、README に含めるコマンド例や .env のサンプル、よくあるトラブルシュート（ログが出ない／DB が作成されない等）を追加で作成します。どの情報をより詳しく載せたいか教えてください。