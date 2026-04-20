# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリのサンプル実装です。  
このリポジトリにはモニタリング、注文実行エンジン（ペーパートレード対応）、ポートフォリオ構築、ファクター計算、LLM を用いたニュース解析などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような用途を想定したモジュール群を提供します。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を行う。`KABUSYS_ENV=paper_trading` では MockBrokerClient を利用し、発注データは専用のペーパートレード DB（`data/paper_trading.db`）に分離して記録します。
- 監視（Monitoring）: システムの稼働状態やオーダーの異常、リスク（ドローダウン・ポジション上限）を定期チェックし、Kill Switch により実行エンジンを安全に停止させる機能を備えます。
- ポートフォリオ構築・サイズ計算: 候補選定、重み算出、ポジションサイズ決定（単元株丸め、リスクベース配分等）。
- リサーチ: DuckDB 上の価格/財務データを利用したファクター計算（Momentum / Volatility / Value）や特徴量研究ユーティリティ。
- AI（LLM）連携: OpenAI API を用いたニュースのセンチメント集約や市場レジーム判定のサポート。
- 開発支援ツール: `.env` 対話ウィザード、設定検証、ペーパートレード検証レポート生成スクリプト等。

---

## 主な機能一覧

- run_execution: 実行エンジン起動スクリプト（Paper/Live 切替、自動 PID / stop フラグ管理）
- run_monitoring: SystemMonitor のポーリングループ起動（ポーリング間隔は環境変数で上書き可）
- config_setup: .env を対話的に作成・更新するウィザード
- validate_config: .env や config/*.yaml の事前検証 CLI
- monitoring: system/ trade / risk の各モニタリング、KillSwitch、Alert 管理
- portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター制約・レジーム乗数
- research: ファクター計算（momentum, volatility, value）、IC 計算など
- ai: ニュース NLP（OpenAI）を使った銘柄別スコアリング、レジーム判定
- tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提（Prerequisites）

- Python 3.10+
- システムにより追加ライブラリ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検証を行う場合)
- 標準で sqlite3 は利用可能（Python 標準ライブラリ）

インストール例（仮想環境の作成推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（パッケージの正確な要件リストは requirements.txt を用意するか、プロジェクトの方針に合わせて管理してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作り、依存をインストール（上記参照）

3. .env を作成・編集
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成/更新します。生成後は必ず `python -m kabusys.validate_config` で検証してください。

   - 手動で作る場合は少なくとも以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて）OPENAI_API_KEY, KABUSYS_ENV 等

   最小例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱い
   python -m kabusys.validate_config --strict
   ```

5. データ / ログ ディレクトリ
   - デフォルトで SQLite / DuckDB / ログファイルは `data/`, `logs/` に配置されます。必要であれば .env の `SQLITE_PATH`, `DUCKDB_PATH`, `LOG_DIR` を変更してください。

---

## 使い方（起動・ツール）

- 実行エンジン（ExecutionEngine）起動
  - 本番/ペーパー切替は KABUSYS_ENV で制御（paper_trading のときは MockBrokerClient を使用）
  ```bash
  # 例: ペーパートレード環境で起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 起動前に `data/stop_requested.flag` が存在すると起動を行いません（注意）。
  - 実行時に `data/execution.pid` に PID を書き込みます。

- 監視（Monitoring）起動
  ```bash
  # ポーリング間隔のデフォルトは 60 秒、環境変数で上書き可
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に「本番用の sqlite_path」を使用して監視ログを永続化します（環境にかかわらず）。停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- .env を作成・更新
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート出力（SQLite DB を指定可能）
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する例
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / リサーチ API の利用（ライブラリとして）
  - ai スコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 4, 20), api_key="YOUR_OPENAI_API_KEY")
    print("scored:", n)
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 20), api_key="...")
    ```

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — LLM 機能を使う場合
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring ポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（0/1）

---

## 停止・再起動・キルフラグ

- 実行エンジン停止シグナル: `data/kill.flag`（KillSwitch が書き込む）。
  - KillSwitch は条件を満たすと `kill.flag` を書き込み、ExecutionEngine 側で停止検出して安全に終了します。
  - KillSwitch を手動でクリアする場合:
    ```python
    from kabusys.monitoring.kill_switch import KillSwitch
    from kabusys.config import Settings
    KillSwitch(Settings().kill_flag_path).clear()
    ```

- 緊急停止（run_* スクリプトの停止）: `data/stop_requested.flag` を作ると起動中のスクリプトは次のポーリング等で停止します。

---

## よくあるトラブルと対処

- 必須環境変数エラー:
  - `JQUANTS_REFRESH_TOKEN` や `KABU_API_PASSWORD` が未設定だと起動しません。`.env` を確認してください。
- ログディレクトリの作成に失敗:
  - 権限やパスを確認。ログ出力は失敗してもコンソール（stdout）には出力されます。
- DuckDB / SQLite のファイルパス:
  - 親ディレクトリが存在しない場合は警告が出ますが、多くは起動時に自動作成されます。パスを手動で作成するか .env を修正してください。
- OpenAI API 呼び出し失敗:
  - `OPENAI_API_KEY` の設定、ネットワーク、API レート制限を確認。LLM 呼び出しはリトライとフェイルセーフを備えていますが、キーが未設定だと例外になります。

---

## ディレクトリ構成（概要）

```
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定管理
    config_setup.py              # .env 対話ウィザード
    validate_config.py           # 設定検証 CLI

    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # SystemMonitor ポーリング起動スクリプト

    utils/
      logging_setup.py           # 統一ロギング設定
      process_priority.py        # プロセス優先度 / CPU affinity
    monitoring/
      monitoring_db.py           # SQLite 永続化層（監視テーブル）
      system_monitor.py          # システム状態・データ鮮度監視
      trade_monitor.py           # 注文ログ監視（滞留・異常検出）  <-- 実装ファイルあり
      risk_monitor.py            # ドローダウン・ポジション上限監視
      kill_switch.py             # kill.flag 書き込み / 監視
      alert_manager.py           # アラート通知（LINE 等）
      monitoring_engine.py       # 各 Monitor を束ねるエンジン

    execution/                   # Execution 関連（OrderManager, BrokerFactory 等）
      order_manager.py
      order_repository.py
      execution_engine.py
      broker_factory.py
      risk_manager.py
      reconciler.py

    portfolio/
      portfolio_builder.py       # 候補選定 / 重み計算
      position_sizing.py         # 株数決定・スケール調整
      risk_adjustment.py         # セクター上限・レジーム乗数

    research/
      factor_research.py         # Momentum / Volatility / Value 等
      feature_exploration.py     # IC / ファクター相関 / 統計サマリー

    ai/
      news_nlp.py                # ニュース -> LLM で銘柄別スコア
      regime_detector.py         # レジーム判定（MA + マクロセンチメント）

    tools/
      paper_verification_report.py  # Paper Trading 検証レポート用 CLI
    ...
```

（上記は主要ファイルのみ抜粋しています。詳細はソースツリーを参照してください）

---

## 開発メモ / 設計上のポイント

- 設計は「本番 API 呼び出しと研究（リサーチ）処理を分離」することを重視しています。DuckDB 上でリサーチを完結させ、発注処理は ExecutionEngine / BrokerClient に閉じます。
- .env 自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を探索して行われます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- モジュールはフェイルセーフ設計（例: LLM 呼び出し失敗時はフォールバック値、DB マイグレーションは冪等）を心がけています。

---

README はここまでです。必要であれば、各モジュール（ExecutionEngine、OrderManager、AlertManager、BrokerClient のモック実装など）の詳細ドキュメント、実行例、ユニットテストのセットアップ手順などを追加で作成できます。どの項目を優先してドキュメント化しましょうか？