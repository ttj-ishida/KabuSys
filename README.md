# KabuSys

日本株向けの自動売買・研究プラットフォーム（スケルトン実装）。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI ベースのニュース解析など、運用に必要な主要コンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的をもつモジュール群で構成されています。

- Execution: 発注／注文管理／リスク管理を行う ExecutionEngine（本番／ペーパートレード対応）。
- Monitoring: システム稼働状況、注文ログ、リスク指標を定期的に監視し、アラートや Kill Switch を発動。
- Portfolio: 銘柄選定、配分、ポジションサイズ計算、セクター制約などのポートフォリオ構築ロジック。
- Research: DuckDB を用いたファクター計算や特徴量探索ツール。
- AI: OpenAI（gpt-4o-mini など）を利用したニュースセンチメント解析および市場レジーム判定。
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト。
- Config: .env の対話的作成ウィザードや設定検証ツール。

設計のポイント:
- 環境依存設定は .env / 環境変数で管理（Settings クラスを介して取得）。
- Paper Trading は本番 DB と完全分離（デフォルト: `data/paper_trading.db`）。
- ロギングは共通ユーティリティで統一（日次ローテート）。
- プロセス優先度や CPU affinity を OS に依存せず扱うユーティリティを提供。

---

## 主な機能一覧

- 起動スクリプト:
  - monitoring（監視ループ）: `kabusys.run_monitoring`
  - execution（発注エンジン）: `kabusys.run_execution`
- 環境設定:
  - 対話式 .env ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- ペーパートレード検証:
  - レポート生成: `kabusys.tools.paper_verification_report`
- ポートフォリオ構築:
  - 候補選定、等重／スコア重み付け
  - ポジションサイズ算出（lot 単位・リスクベース等）
  - セクター上限適用、レジーム乗数
- 研究用ファクター計算:
  - モメンタム、ボラティリティ、バリュー等（DuckDB ベース）
  - 将来リターン・IC（Spearman）計算、統計サマリー
- AI:
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA + LLM 合成）
- 監視・リスク:
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - Kill Switch（`data/kill.flag`）生成・評価
  - stop フラグ（`data/stop_requested.flag`）でループ停止

---

## 要件（例）

- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 仮想環境推奨: venv / poetry など

インストール例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を用意する。

2. 環境変数ファイルを作成する（推奨は対話式ウィザード）:
   ```bash
   python -m kabusys.config_setup
   ```
   主要な環境変数（一部、デフォルト値）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
   - PAPER_FILL_MODE (paper_trading 用: instant|partial|never|reject)
   - PAPER_TRADING_SQLITE_PATH （paper_trading 用 DB パス）

3. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. DB の準備:
   - 初回起動時、必要なディレクトリ（data/、logs/）は自動作成されることが多いですが、権限等で失敗する場合は手動で作成してください。
   - DuckDB / SQLite のファイルパスは .env で指定できます。

5. OpenAI を利用する場合:
   - 環境変数 `OPENAI_API_KEY` を設定してください（AI 機能を使う際に必要）。

---

## 使い方（起動コマンド例）

- 監視プロセスを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。
  - 監視ループはプロジェクトルートの `data/stop_requested.flag` ファイルの存在を検出して終了します。

- 実行エンジン（ExecutionEngine）起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用 DB（デフォルト: `data/paper_trading.db`）に記録します。
  - Execution は `data/stop_requested.flag` の検出で停止します。実行時は PID を `data/execution.pid` に書きます。

- ペーパートレード検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI/研究モジュールの利用はライブラリ経由で:
  - ニューススコアリング（プログラムから）:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: DuckDB 接続, target_date: datetime.date
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジームスコア:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```

- ログ:
  - デフォルトログディレクトリ: `logs/`
  - ログファイル名はアプリ名（例: `execution.log`, `monitoring.log`）
  - ログレベルは環境変数 `LOG_LEVEL` または `setup_logging` の引数で制御

---

## フラグ・ファイル（運用上の注意）

- 停止リクエスト:
  - data/stop_requested.flag — run_* スクリプトがこれを検出すると安全にループを終了します（手動で作成することで停止させられます）。
- Kill Switch:
  - data/kill.flag — KillSwitch がリスク条件を満たした場合に書き込まれ、ExecutionEngine に停止シグナルを与える用途で使われます。
  - `KILL_FLAG_CLEAR_ON_START` 環境変数が `1` のとき起動時に自動クリアされます（本番では通常 `0` 推奨）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリが src/kabusys 配下でパッケージ化されている想定）

- src/kabusys/
  - __init__.py
  - run_monitoring.py           — 監視ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - config.py                   — 環境変数 / Settings クラス
  - config_setup.py             — .env ウィザード
  - validate_config.py          — 設定検証 CLI
  - utils/
    - logging_setup.py          — 統一ロギング設定
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py          — SQLite 永続化（system_status 等）
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — 注文滞留・約定異常検出（※実装参照）
    - risk_monitor.py           — ドローダウン／ポジション上限監視
    - kill_switch.py            — Kill Switch の評価 / フラグ管理
    - alert_manager.py          — （アラート送信ロジックを想定）
    - monitoring_engine.py      — 各 Monitor を束ねる実行ループ
  - execution/
    - execution_engine.py       — ExecutionEngine 本体（発注ループ等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py         — Broker クライアント生成（Mock / 実装分岐）
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
    - news_nlp.py               — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py        — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - data/                        — 実行時に生成される SQLite / DuckDB / flag / pid 等（デフォルト）

※上記は主要なファイルの抜粋です。詳細はソースを参照してください。

---

## 設定例（.env のサンプル行）

例（実運用では秘密情報は必ず安全に管理すること）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
PAPER_FILL_MODE=instant
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 運用上の注意 / ベストプラクティス

- 本番 (KABUSYS_ENV=live) では必須環境変数が整っていることを `validate_config` で事前にチェックしてください。
- Kill Switch / stop flag の誤操作を避けるため、ファイルの作成・削除は慎重に行ってください。
- OpenAI API など外部 API 呼び出しはレート制限・課金リスクがあるため、キー管理と呼び出し頻度に注意してください。
- ログは `logs/` に日次ローテーションで保存されます。ディスク容量の監視を行ってください。
- psutil によるプロセス優先度設定は権限に依存します。権限不足時は警告のみ出て処理は継続します。

---

## 貢献 / 拡張ポイント（アイデア）

- ブローカークライアントの具体実装（kabuステーション API）や認証フローの追加。
- 単元株サイズや手数料モデルを銘柄別に持たせる拡張。
- AI モデルの出力検証・キャリブレーション用のテストパイプライン。
- アラート配送（LINE・Slack・メール）の pluggable 実装。
- 単体テストや CI の追加、型チェック強化（mypy）や lint（flake8）整備。

---

README に記載のない内部 API や細かい実装はソースコード内の docstring を参照してください。必要であれば、特定モジュールの使い方や API 仕様をより詳細にまとめます。どの箇所を優先してドキュメント化しましょうか？