# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連する監視・リサーチ機能を備えたシステムです。  
主な目的は以下です。

- データ収集・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（銘柄選定、配分、ポジションサイズ計算）
- 発注実行エンジン（kabuステーション API / モック）
- 監視（システム状態、注文ログ、リスク監視）と Kill Switch
- Paper Trading 検証レポート生成
- ニュース NLP やレジーム判定などの AI 補助機能（OpenAI を利用）

本リポジトリは、実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替え可能な設計になっています。

---

## 主な機能一覧

- ExecutionEngine：発注・注文管理・リコンサイル・リスク管理（実口座 / ペーパートレード切替）
- Monitoring：定期ポーリングによるシステム監視・データ鮮度チェック・アラート生成・Kill Switch
- MonitoringDB：SQLite を用いた監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Portfolio モジュール：候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- Research モジュール：ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン、IC 計算
- AI モジュール：
  - news_nlp: ニュース記事を OpenAI で評価し銘柄毎のスコアを ai_scores に格納
  - regime_detector: ETF MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- CLI 補助ツール：
  - 環境設定ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading の検証レポート生成（tools.paper_verification_report）

---

## 必要要件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の構文チェックに利用）

開発環境では仮想環境（venv / pyenv-virtualenv など）の利用を推奨します。

例（UNIX 系）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際に必要なパッケージはプロジェクトの requirements.txt に合わせてください（本コードベースに requirements.txt は含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env ファイルを作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは `.env` を生成・更新します。生成後は以下で設定検証を行ってください。

5. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

---

## 使い方（実行例）

- 環境設定ウィザード（.env を作る）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  備考:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、data/paper_trading.db に記録されます（本番 DB と分離）。
  - エンジンはデフォルトで PID ファイル（data/execution.pid）を使用し、停止フラグ（data/stop_requested.flag）を検出すると停止します。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  備考:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  - 監視コンポーネントは常に本番の sqlite_path を利用します（環境にかかわらず）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション `--db PATH` で SQLite ファイルを直接指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

---

## 停止・Kill Switch の挙動

- 手動で ExecutionEngine を停止するにはリポジトリの data ディレクトリに停止フラグファイルを書きます:
  - 停止リクエスト（run_execution のループ検出用）: data/stop_requested.flag
  - Kill Switch（監視が条件を満たした際に作成される）: data/kill.flag
- KillSwitch はリスク監視やドローダウン等の条件が成立した場合に `data/kill.flag` を書き込みます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていれば自動でクリアされます（本番では 0 推奨）。

---

## ログ設定

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を利用してログを統一管理します。
- デフォルトは stdout へ出力（StreamHandler）と `logs/<app_name>.log` へ日次ローテート（TimedRotatingFileHandler）です。
- ログディレクトリは LOG_DIR 環境変数、もしくはデフォルト `logs/`。

---

## 注意点・設計上のポイント

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離され、専用 SQLite（data/paper_trading.db）を使用します。
- AI 機能（news_nlp / regime_detector）は OpenAI の API を使用します。OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバック（失敗時スコア=0 等）を組み込んで安全側で動作します。
- コンポーネントはできる限り副作用を抑え、DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を保つよう実装されています。
- プロセス優先度設定（psutil 利用）や CPU affinity 設定機能がありますが、環境権限により失敗する場合は警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイル・パッケージ）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — 環境設定ウィザード（.env 生成）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文ログ監視等）※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — Kill Switch ファイル操作
    - alert_manager.py       — （アラート送信管理）※実装ファイルあり
  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体）※実装ファイルあり
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文履歴 DB 操作
    - broker_factory.py      — ブローカークライアント生成（Mock 含む）
    - risk_manager.py        — 発注前リスクチェック
    - reconciler.py          — 注文とブローカー状態の整合
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み
    - position_sizing.py     — 株数算出・スケールダウン
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - data/                    — （デフォルトの DB/flag/pid が置かれる想定）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。実際の補助モジュールや実装ファイルが他にも存在します。）

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

必要であれば、README に動作フロー図・各コンポーネントのシーケンスや、.env 例（.env.example の抜粋）、デプロイ手順（systemd / supervisor / Dockerfile など）を追加します。追加希望があれば教えてください。