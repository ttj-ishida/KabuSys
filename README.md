# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリには、発注エンジン・監視・ポートフォリオ構築・リサーチ・AI ベースのニュース解析など、実運用を想定したコンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要要件
- セットアップ手順
- 環境変数・設定
- 実行方法（使い方）
- 停止 / Kill スイッチについて
- ディレクトリ構成（概観）

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。以下の領域をカバーします。

- ExecutionEngine（発注処理、ブローカークライアント抽象化、リスク管理）
- Monitoring（システム稼働監視、注文/約定ログ、リスク検知、Kill Switch）
- Portfolio construction（候補選定・重み付け・ポジションサイズ算出・セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI（ニュースのセンチメント解析、レジーム判定 — OpenAI を利用）
- Tools（Paper Trading 検証レポート生成など）
- 開発用ユーティリティ（.env ウィザード、設定検証、ログ設定、プロセス優先度設定）

設計方針として、可能な限り副作用を抑え、DB パスを環境変数で分離し、ペーパートレード用 DB を本番 DB と完全に分離できるようになっています。

---

## 主な機能（機能一覧）

- 環境毎の挙動切替（development / paper_trading / live）
- .env 対話式ウィザードによる初期設定（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合はモックブローカー、専用 DB（data/paper_trading.db）を使用
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - システム状態・データ鮮度・トレードログ等の定期チェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（デフォルト 60 秒）
- Kill Switch（監視条件により data/kill.flag を書き込み、ExecutionEngine に停止を指示）
- RiskMonitor（ドローダウン/ポジション上限の監視とログ記録）
- AI モジュール
  - news_nlp: raw_news を LLM でスコアリングして ai_scores に格納
  - regime_detector: MA200 とマクロニュースを合成して市場レジーム判定
- Portfolio モジュール（候補選定、等金額・スコア重み、ポジションサイズ計算、セクターキャップ）
- Research（ファクター計算、Forward return、IC、統計サマリー）
- Tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

---

## 必要要件

- Python 3.10+（ソースでパイプ型ヒント `|` を使用）
- 推奨パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- （任意）SQLite（標準ライブラリ sqlite3 を使用）
- （任意）ネットワーク接続（OpenAI API を利用する場合）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# 実際は requirements.txt があれば `pip install -r requirements.txt` を推奨
```

---

## セットアップ手順

1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存パッケージインストール（上記参照）

3. .env の初期作成（対話式ウィザード）:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードに従い、必須のリフレッシュトークンや kabu API パスワードなどを設定します。

4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 厳密モード（警告を FAIL とする）
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリ（デフォルト: logs/）や data/ ディレクトリは通常起動時に自動作成されますが、必要に応じて手動で作成してください。

6. 環境変数の自動読み込み:
   - リポジトリルートに `.env` / `.env.local` が存在する場合、起動時に自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数・主な設定項目

主に `.env` で設定する項目（一部とデフォルト）:

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）

- データベース:
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用 DB）

- OpenAI:
  - OPENAI_API_KEY（ai.news_nlp / regime_detector を使用する場合）

- ログ:
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: logs/（デフォルト）

- Paper Trading 挙動:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- その他:
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（0/1。起動時の kill.flag 自動クリア。デフォルト: 0）

注意: .env ウィザード（config_setup.py）で多くのキーを対話式に設定できます。

---

## 実行方法（使い方）

- ExecutionEngine（発注エンジン）を起動:
  - 本番/開発/ペーパーは KABUSYS_ENV で制御。
  - ペーパートレードでは MockBrokerClient を使用し、paper_trading 用 DB に記録します。
  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring（監視）を起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に (settings.sqlite_path) を使用して監視用 sqlite DB に書き込みます（環境に依存せず）。
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート:
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定する例
  python -m kabusys.tools.paper_verification_report --db /path/to/custom_paper.db
  ```

- ライブラリとして利用:
  - 研究・ポートフォリオ関数や AI スコアリング関数はモジュールとしてインポートして利用できます（例: kabusys.research.calc_momentum, kabusys.portfolio.calc_position_sizes, kabusys.ai.score_news など）。

---

## 停止 / Kill スイッチについて

- 停止フラグ:
  - プロセスの外部から安全に停止させる目的で、プロジェクトの data/ ディレクトリにフラグファイルを置く仕組みがあります。
  - run_monitoring/run_execution は data/stop_requested.flag の存在を検知して安全にシャットダウンします。

- Kill Switch（リスクによる強制停止）:
  - 監視コンポーネント（RiskMonitor など）がしきい値を超えた場合、kill_switch が data/kill.flag に理由を書き込みます。
  - ExecutionEngine は起動時に kill.flag の存在を確認し、既に立っている場合は起動を中止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0（非クリア）を推奨します。

- PID ファイル:
  - ExecutionEngine は起動時に PID ファイル（settings.pid_file_path）を作成します（例: data/execution.pid）。外部ツールからプロセスを管理する際に利用できます。

---

## ログについて

- 共通ロギングセットアップを行うユーティリティがあり、すべての起動スクリプトで呼ばれます。
- 出力先:
  - コンソール stdout（StreamHandler）
  - 日次ローテーションするファイル: logs/<app_name>.log（TimedRotatingFileHandler、30 日保管）
- LOG_DIR / LOG_LEVEL 環境変数で挙動を制御します。

---

## ディレクトリ構成（概観）

以下は主なファイル・パッケージの一覧（src/kabusys 以下を抜粋）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定取得ユーティリティ（Settings）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - execution/              — 発注周り（Engine, OrderManager, BrokerFactory 等）（参照あり）
  - monitoring/
    - monitoring_db.py      — SQLite 永続層（テーブル作成・CRUD）
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文/約定の整合性チェック（参照あり）
    - risk_monitor.py       — ドローダウン / ポジション数監視
    - monitoring_engine.py  — 各 Monitor を束ねる
    - kill_switch.py        — kill.flag 書き込みロジック
    - alert_manager.py      — アラート通知（参照あり）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み付け
    - position_sizing.py    — 株数決定・投下資金キャップ
    - risk_adjustment.py    — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py    — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — Forward returns, IC, summary
    - __init__.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 呼び出し・バッチ処理・書込み）
    - regime_detector.py    — レジーム判定（MA200 + マクロセンチメント）
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU Affinity 設定
    - __init__.py

その他:
- data/                   — デフォルトデータディレクトリ（DB、PID、フラグ等を配置）
- logs/                   — ログ保存ディレクトリ（デフォルト）

（上記は主要ファイルを抜粋した構成です。発注関連や追加のユーティリティは execution/ 以下にあります。）

---

## 追加の注意点 / ベストプラクティス

- 本番環境では KABUSYS_ENV=live を設定し、LINE 通知などの運用用設定を必ず確認してください。
- paper_trading は本番 DB と完全分離されるため安全に検証可能です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI 利用機能（news_nlp / regime_detector）を使う際は API キーの漏洩に注意し、レート制限や費用管理を行ってください。
- .env は決して Git にコミットしないでください（config_setup にもその旨の警告があります）。
- 監視・停止の仕組みはファイルベース（data/kill.flag, data/stop_requested.flag）で実装されており、外部の運用スクリプトから簡単に制御できます。

---

ご不明点や README に追記してほしい内容があれば教えてください。README の例の .env テンプレートや起動スクリプトのサンプル systemd サービスユニット等も必要であれば作成します。