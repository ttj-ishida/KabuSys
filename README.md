# KabuSys

日本株向け自動売買システムのリポジトリ（プロトタイプ）。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（実口座 / ペーパートレード）、監視・アラート、AI を使ったニュースセンチメント評価などの機能を含みます。

---

## 概要

KabuSys は以下を目的としたモジュール群から構成される自動売買基盤です。

- ファクター計算・研究（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 発注実行エンジン（本番とペーパートレードを分離）
- 監視（システム稼働、注文状態、リスク監視、Kill Switch）
- AI によるニュースセンチメント評価（OpenAI）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部：
- DuckDB / SQLite をデータ層に利用（分析用は DuckDB、稼働監視等は SQLite）
- .env ベースの環境設定（自動読み込み機能あり）
- 本番 / ペーパートレードを明確に分離（DB、ブローカークライアント等）
- ロギングは統一されたユーティリティで stdout + 日次ローテートファイル出力

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
- Monitoring 起動（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に参照（環境に依らず）
- モニタリングエンジン（各種モニタをまとめて実行）
  - SystemMonitor（CPU/MEM/DISK、データ鮮度、実行プロセスの死活など）
  - TradeMonitor（滞留注文／約定異常検出）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（危険条件で data/kill.flag を書き込み ExecutionEngine を停止）
- 研究モジュール
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索、IC 計算、統計サマリー
- AI モジュール
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores へ書き込み）
  - regime_detector: MA とマクロニュースを組み合わせて市場レジーム判定
- 運用ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

---

## セットアップ手順

前提
- Python 3.10+（型ヒントで | を使用しているため 3.10 以上を推奨）
- システムにより追加で以下が必要になる場合があります: build ツール等

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   代表的なパッケージ（requirements.txt がない場合は手動でインストールしてください）:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - openai: AI 機能を使う場合
   - PyYAML: validate_config が YAML の構文チェックを行うときに必要

4. .env の作成  
   対話式ウィザードを使うのが簡単です：
   ```
   python -m kabusys.config_setup
   ```
   もしくはルートに `.env` を作成して必要な環境変数を設定します。自動読み込みはデフォルトで有効（プロジェクトルートに .env があるとロードされます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   本番前は `--strict` を付けることを推奨します（警告も失敗扱いになります）。

6. ディレクトリ作成（ログ・DB 保存先など）
   - `data/`（DB・フラグファイル保存）
   - `logs/`（ログ）
   通常は logging_setup が自動作成しますが、アクセス権限に注意してください。

---

## 主要な環境変数（抜粋）

以下は Settings クラスで参照される主なキーとデフォルト／意味の抜粋です。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用 DB（常に本番 path を参照）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — ペーパートレード専用 DB
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
- MONITOR_POLL_INTERVAL (run_monitoring.py のポーリング間隔 秒、デフォルト 60)
- PAPER_FILL_MODE (instant | partial | never | reject)（ペーパートレードの約定挙動）

サンプル .env（最低限のキー）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（実行例）

- ExecutionEngine を起動（デフォルト: 設定に従う）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレードで起動する場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    paper_trading のときは MockBrokerClient が使われ、発注履歴は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する（秒）
    ```
    export MONITOR_POLL_INTERVAL=120
    python -m kabusys.run_monitoring
    ```

- 停止方法
  - 実行中の run_execution / run_monitoring は `data/stop_requested.flag` の存在を監視しており、ファイルが存在するとループを抜けます（スクリプトがそのフラグを参照して停止処理を行います）。
  - KillSwitch（リスクトリガ）により `data/kill.flag` が書かれると ExecutionEngine 側で停止処理が走ります。

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env の初期作成
  ```
  python -m kabusys.config_setup
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（news_nlp / regime_detector）を使う際は必ず OPENAI_API_KEY を設定してください。

---

## ロギング

- 共通ロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" | "monitoring" ...)
- 出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテート、30 日保持）
- LOG_DIR 環境変数でログ保存先を変更可能。

---

## ディレクトリ構成（抜粋）

リポジトリの主要モジュール構成は以下の通りです（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 等分配・スコア配分
    - position_sizing.py     — 発注株数算出、集約キャップ処理
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ初期化・永続化ラッパー
    - system_monitor.py      — CPU/MEM/DISK・データ鮮度・プロセス監視
    - trade_monitor.py       — 注文・約定の監視（※実装ファイルは別途）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch の判定・フラグ書き込み
    - monitoring_engine.py   — モニタ群を束ねる実行エンジン
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（注）ここに示したのは主要ファイルの抜粋です。実際のリポジトリには execution パッケージや data 管理用の他コンポーネントが含まれます。

---

## 運用上の注意点

- KABUSYS_ENV は必ず正しい値（development | paper_trading | live）を設定してください。`live` は本番なので慎重に設定すること。
- 本番環境では KILL_FLAG_CLEAR_ON_START は 0（自動クリアしない）を推奨します。
- AI 機能を使う場合は API レート制限やコストを考慮してください（OpenAI の呼び出しはリトライ等の制御あり）。
- Run スクリプトはフラグファイル（data/stop_requested.flag, data/kill.flag）で停止・制御する仕組みです。運用手順を明確にしてください。
- ログ / DB の保存先ディスク容量に注意してください（特に DuckDB やログのローテーション）。

---

## 参考コマンドまとめ

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

何か特定のモジュールについて詳しいドキュメント（関数の使い方、設定項目の詳細、実行フロー図など）が必要であれば教えてください。追加で README に図やサンプルワークフロー、設定テンプレートを追記できます。