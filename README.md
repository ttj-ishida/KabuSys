# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）。  
このリポジトリは、データ処理・ファクター計算・ポートフォリオ構築・発注（実行）・監視・AI 補助（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

目次
- 概要
- 主な機能
- 環境要件と依存パッケージ
- セットアップ手順
- 主要コマンド／使い方
- 重要な環境変数（.env）
- 停止 / キルスイッチの扱い
- ディレクトリ構成（主要ファイル説明）
- 補足（注意点）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な責務は次の通りです。

- データ基盤（DuckDB／SQLite）を使ったファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 発注エンジン（ExecutionEngine） — 本番/ペーパートレード切替対応
- 監視コンポーネント（System/Trade/Risk）と Kill Switch
- AI によるニュースセンチメント（OpenAI API）やレジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計上の特徴：
- 環境変数 / .env による設定管理
- DuckDB を分析用途、SQLite を監視・発注ログ用途に利用
- 本番 DB とペーパートレード DB を明確に分離
- OpenAI 呼び出しはフェイルセーフ（API 失敗時は安全側フォールバック）

---

## 主な機能一覧

- 環境設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 実行用エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading で MockBroker を使用し、data/paper_trading.db に記録
- 監視 (Monitoring) 起動スクリプト（kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）
- 監視用 DB 層（monitoring_db）と各種モニタ（System/Trade/Risk）
- Kill Switch（リスクトリガで data/kill.flag を書き込み Execution を停止）
- ポートフォリオ構築ユーティリティ（候補選定・重み・ポジションサイズ等）
- Research モジュール（ファクター計算、前方リターン、IC 計算、統計サマリ）
- AI モジュール（ニュース NLP による銘柄スコア / レジーム判定、OpenAI 利用）
- 運用ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 環境要件と依存パッケージ

必須（最低限）:
- Python 3.10+（| 型注釈や match を利用しないが、Union 縮約 (A | B) を使用）
- duckdb
- psutil
- openai

オプション（機能依存）:
- PyYAML（config/*.yaml の内容検証用、validate_config で使う）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がない場合は上記を参考に必要なパッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンしてソースに移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードで作成する場合:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で .env を作成（後述のサンプル参照）。
5. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要に応じて data/ ディレクトリなどを作成（ログや DB の初期配置は自動作成される場合があります）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine（発注エンジン）起動
  - 本番（KABUSYS_ENV=live 等）または paper_trading（PAPER_TRADING 用 DB を使用）
  ```bash
  python -m kabusys.run_execution
  ```
  - ExecutionEngine は data/execution.pid に PID を書き、data/stop_requested.flag を検知して停止します。
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 専用 DB（デフォルト: data/paper_trading.db）に記録されます。

- Monitoring（監視）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（monitoring DB）を常に使用します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - OpenAI API キー（OPENAI_API_KEY）が必要。ニューススコアやレジーム判定は専用関数を呼び出します（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime 等）。

---

## 重要な環境変数（.env）

主なものを抜粋します。詳しくは `kabusys/config_setup.py` を参照してください。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動消去するか（0/1。本番では 0 推奨）

例（.env の要点）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0
```

---

## 停止 / キルスイッチの扱い

- run_execution / run_monitoring はプロセス制御用のフラグファイルを参照します:
  - data/stop_requested.flag — ループプロセスの優雅な終了トリガ。存在するとループを抜けます（run_monitoring, run_execution が参照）。
  - data/kill.flag — Kill Switch（監視が条件を満たすと書き込まれる）。ExecutionEngine 側で検出されると停止します。

- KillSwitch はリスクやポジション上限のトリガで kill.flag を書き込みます。既に存在する場合は再書き込みしません（冪等）。

- run_execution は data/execution.pid に PID を書きます（プロセス管理やステータス確認に利用）。

- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。無効値や 0 はデフォルト 60 秒にフォールバックします。

---

## ロギング

- ログ設定は kabusys.utils.logging_setup.setup_logging により統一管理されます。
- デフォルトでは stdout に出力しつつ、日次ローテーションで logs/<app_name>.log に出力されます（30 日保持）。
- LOG_DIR 環境変数でログディレクトリを変更可能。ディレクトリ作成失敗時はファイル出力は無効化されコンソールのみになります。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのメタ情報（__version__ 等）

- config.py
  - 環境変数・.env 自動読み込み、Settings クラス（各種設定プロパティ）

- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前に環境設定と config/*.yaml を検証する CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV によりペーパー/本番切替

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity の設定ユーティリティ
  - など

- monitoring/
  - monitoring_db.py — SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/DISK/データ鮮度/実行プロセス監視
  - trade_monitor.py — （滞留注文・約定異常等の監視）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 複数 Monitor を束ねた実行ループ
  - alert_manager.py — （アラート送信ロジック、LINE など。実装参照）

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等（発注ロジック）
  - （注）発注周りは本番 API とのインターフェースを持つため設定に注意

- portfolio/
  - portfolio_builder.py — 候補選定、等金額 / スコア重み
  - position_sizing.py — 取付株数算出（lot 単位丸め・資金スケール）
  - risk_adjustment.py — セクター上限、レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB クエリ中心）
  - feature_exploration.py — 将来リターン、IC、統計サマリ等

- ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロ NLP を合成して market_regime を判定

- tools/
  - paper_verification_report.py — ペーパートレード DB を解析してレポート生成

---

## 補足 / 注意点

- OpenAI を利用する機能は API 利用料が発生します。OPENAI_API_KEY を必ず管理してください。
- 本番運用時は KABUSYS_ENV=live を指定し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- .env ファイルは絶対にリポジトリへコミットしないでください（config_setup の冒頭にも警告あり）。
- DuckDB / SQLite のパスはデフォルトで data/ 下を想定しています。必要に応じて .env で変更してください。
- validate_config は PyYAML が無ければ YAML の中身検証をスキップします（存在確認は行います）。
- 一部のファイルでは OS 権限や psutil がアクセス拒否を返す場合、警告を出して処理を継続するフェイルセーフ設計になっています。

---

必要に応じて README に追記します。運用ルール（デプロイ手順・監視アラート先・Broker の設定等）を反映したい場合は、ご希望の細かさで追加してください。