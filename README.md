# KabuSys

日本株自動売買システム（KabuSys）のREADME。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（本番 / ペーパートレード）を想定した総合フレームワークです。  
主な設計方針：

- 実行ロジック（ExecutionEngine）と監視（Monitoring）を明確に分離
- DuckDB / SQLite を利用した分析・監視データの永続化
- OpenAI（LLM）を使ったニュースのセンチメント解析や市場レジーム判定（オプション）
- 環境変数 / `.env` による設定管理、対話式ウィザードと検証ツールを提供
- ペーパートレード時は本番 DB と完全分離（`data/paper_trading.db`）

---

## 機能一覧

- 実行（Execution）
  - BrokerClient 抽象化（本番 / モックの切替）
  - 発注管理、リスク管理、照合（reconciler）
  - ペーパートレード用の専用 DB 分離
- 監視（Monitoring）
  - システムリソース（CPU/メモリ/ディスク）と Execution プロセス監視
  - 注文ログ / 約定ログの監視（滞留注文、異常約定など）
  - リスク監視（ドローダウン・ポジション数上限）
  - Kill Switch（条件が揃うと `data/kill.flag` を書き込み Execution を停止）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、リスクベースの株数計算
  - セクター集中制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で処理）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI（オプション）
  - ニュースのセンチメントスコアリング（OpenAI）
  - マクロセンチメント + ETF MA200 に基づく市場レジーム判定
- ツール
  - ペーパートレード検証レポート生成（過去期間の稼働率・成功率・レイテンシ等を集計）
- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - `.env` 作成ウィザード、設定検証 CLI

---

## 要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- （任意）OpenAI API を使う場合は `OPENAI_API_KEY` を設定

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
※ 実際の requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存パッケージインストール（上記参照）

3. 初期設定（.env）
   - 対話式ウィザードを使う（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは `.env` を生成・更新します。シークレット値はマスク表示されます。
   - もしくは `.env.example` を参考に手動で `.env` を作成してください。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等の確認
   - デフォルト DB 等は以下（必要に応じて `.env` で上書き）
     - DuckDB: `data/kabusys.duckdb` (`DUCKDB_PATH`)
     - SQLite（監視）: `data/monitoring.db` (`SQLITE_PATH`)
     - ペーパートレード SQLite: `data/paper_trading.db` (`PAPER_TRADING_SQLITE_PATH`)
   - ログは `logs/` に出力（`LOG_DIR` で変更可）

---

## 使い方（実行例）

- 監視ループ起動
  - 環境変数:
    - `MONITOR_POLL_INTERVAL`：ポーリング間隔秒（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を参照（設計上の挙動）
  ```bash
  python -m kabusys.run_monitoring
  ```

- Execution エンジン起動
  - `KABUSYS_ENV=paper_trading` の場合はモックブローカーを使い、ペーパートレード専用 DB に記録します
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中に停止させたい場合はプロジェクトの `data/stop_requested.flag` を作成（監視 / 実行スクリプトはこのファイルを検知して停止処理を行います）。
  - `data/kill.flag` はシステム側の Kill Switch（条件を満たした際に書き込まれる）で、Execution を停止させるために使用します。

- .env 作成ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```bash
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラム的に呼び出す）
  - ニューススコアリング:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - `api_key` 未指定時は環境変数 `OPENAI_API_KEY` を使用
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 注意: OpenAI 呼び出しは失敗時にフェイルセーフで継続する設計（多くのケースで 0.0 等にフォールバック）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照）

自動読み込み:
- プロジェクトルートに `.env` / `.env.local` があれば自動的に読み込まれます（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

---

## 停止制御 / フラグファイル

- data/stop_requested.flag
  - 起動スクリプト（run_monitoring / run_execution）はこのファイルの存在を監視し、存在時に安全にシャットダウンします。
- data/kill.flag
  - KillSwitch が危険条件（ドローダウン超過など）を検出した場合に書き込まれるファイル。ExecutionEngine を停止させるために使用されます。
- PID ファイル
  - 実行エンジンは PID ファイルを `data/execution.pid`（設定により上書き可能）に書きます。

---

## ディレクトリ構成（抜粋）

```
src/kabusys/
├─ __init__.py
├─ config.py                 # 環境変数 / Settings クラス（.env 自動読み込みロジック含む）
├─ config_setup.py           # .env 対話式ウィザード
├─ validate_config.py        # 設定検証 CLI
├─ run_monitoring.py         # SystemMonitor ポーリングループ起動スクリプト
├─ run_execution.py          # ExecutionEngine 起動スクリプト
├─ utils/
│  ├─ logging_setup.py       # 統一的ログ設定（コンソール + 日次ファイルローテート）
│  ├─ process_priority.py    # プロセス優先度 / CPU affinity 設定ユーティリティ
│  └─ __init__.py
├─ monitoring/
│  ├─ monitoring_db.py       # SQLite テーブル初期化 + 永続化層 API
│  ├─ system_monitor.py      # システム状態・データ鮮度チェック
│  ├─ trade_monitor.py       # （注文監視ロジック）
│  ├─ risk_monitor.py        # ドローダウン・ポジション上限チェック
│  ├─ kill_switch.py         # Kill Switch 制御（kill.flag 書込）
│  ├─ monitoring_engine.py   # 各 Monitor を束ねるポーリングエンジン
│  └─ ...
├─ execution/
│  ├─ execution_engine.py    # ExecutionEngine（起動 / run_session 等）
│  ├─ order_manager.py       # 注文管理
│  ├─ order_repository.py
│  ├─ reconciler.py
│  └─ broker_factory.py      # Broker クライアントの生成（本番/モック）
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  ├─ risk_adjustment.py
│  └─ __init__.py
├─ research/
│  ├─ factor_research.py     # Momentum/Volatility/Value などの計算
│  ├─ feature_exploration.py # 将来リターン / IC / 統計サマリー
│  └─ __init__.py
├─ ai/
│  ├─ news_nlp.py            # ニュース -> センチメントスコア（OpenAI）
│  ├─ regime_detector.py     # レジーム判定（MA200 + マクロセンチメント）
│  └─ __init__.py
├─ tools/
│  ├─ paper_verification_report.py  # ペーパートレード検証レポートジェネレータ
│  └─ __init__.py
└─ ...
```

各ファイル・モジュール内にドキュメンテーション（docstring）が充実しており、関数単位での設計目的や引数仕様が記載されています。まずは `config_setup.py` で `.env` を作成し、`validate_config.py` でチェックした後、`run_execution.py` / `run_monitoring.py` を順に起動するワークフローを推奨します。

---

## 開発上の注意点 / 補足

- Python の型ヒントや modern syntax（`|` 型など）を使用しているため Python 3.10 以上が必要です。
- DuckDB は分析用、SQLite は軽量な監視／履歴保存用に使い分けています。
- OpenAI 呼び出し部分はネットワークエラーやレート制限に対してリトライ戦略を持ちますが、API 使用料が発生します。実行前に必ず `OPENAI_API_KEY` をセットしてください。
- ロギングはデフォルトで `logs/<app_name>.log` に日次ローテートで保存されます。ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみとなります。
- 本番（`KABUSYS_ENV=live`）では `validate_config` が注意喚起を出します。設定は慎重に行ってください。

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 監視起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 実行エンジン起動:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README の各セクションをさらに詳細化（API ドキュメント抜粋、設定例 `.env.example`、実行時のログ例、テスト方法など）します。どの情報を優先して追加しますか？