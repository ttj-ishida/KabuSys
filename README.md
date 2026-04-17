# KabuSys

日本株自動売買システムの一部コンポーネント群（設定管理・実行エンジン起動スクリプト・監視・ポートフォリオ構築・リサーチ・AI補助モジュール 等）。

このリポジトリ（src/kabusys 以下）は、発注エンジンの実行・監視、ペーパートレード検証、ファクター/リサーチ、ニュースNLP によるスコアリングなどのユーティリティを含みます。

---

## プロジェクト概要

- 実行環境（development / paper_trading / live）を切り替え可能な自動売買向けツール群。
- ExecutionEngine（発注エンジン）と Monitoring（監視）の起動スクリプトを提供。
- ペーパートレード時は本番 DB と分離して記録（MockBroker を使用）。
- DuckDB を用いたファクター計算・リサーチ機能。
- OpenAI を用いたニュースセンチメント解析（news_nlp）および市場レジーム判定（regime_detector）。
- 監視ログは SQLite（monitoring.db）へ永続化。監視により Kill Switch を発動して実行エンジンを安全に停止できる。

---

## 主な機能一覧

- 設定管理
  - .env ウィザード（kabusys.config_setup）で初期 .env を対話形式で作成／更新
  - 設定検証 CLI（kabusys.validate_config）で環境変数／config/*.yaml の事前チェック

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper/live 動作）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（デフォルト 60 秒間隔）
  - Kill Switch / stop フラグで安全に停止（data/kill.flag、data/stop_requested.flag 等）

- 監視・アラート
  - SystemMonitor: プロセス、生データ鮮度、CPU/メモリ/ディスク検査
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringDB: SQLite への監視ログ永続化層

- ポートフォリオ構築
  - 候補選定、等重・スコア重みの算出、ポジションサイズ決定、セクターキャップ、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等

- AI（OpenAI）連携
  - news_nlp: ニュース記事を集約してセンチメントを LLM でスコア化し ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成して日次レジーム判定

- ツール
  - paper_verification_report: ペーパートレード DB から PASS/FAIL 判定と指標を出力

---

## 必要要件（依存パッケージ）

主に以下のライブラリを使用します（実行環境に応じて追加）。

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — config/*.yaml のパース検証で使用

インストール例（venv を推奨）:
```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージ配置（パッケージが src/kabusys 配下に存在することを前提）。

2. 仮想環境の作成（任意）:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
pip install -U pip
```

3. 必要パッケージのインストール:
```bash
pip install duckdb psutil openai pyyaml
```

4. .env の初期作成（対話ウィザード）:
```bash
python -m kabusys.config_setup
```
ウィザードに従い、必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。
※ .env は絶対に Git にコミットしないでください。

5. 設定検証（任意）:
```bash
python -m kabusys.validate_config
# 警告をエラー扱いにしたい場合:
python -m kabusys.validate_config --strict
```

6. DB ファイル・data ディレクトリ等の準備は多くの場合自動作成されます。必要に応じて DUCKDB_PATH / SQLITE_PATH を .env で指定してください（デフォルトは data/kabusys.duckdb、data/monitoring.db）。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定振る舞い（instant|partial|never|reject。デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、デフォルト 0、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（デフォルトは data/ 下）

---

## 使い方（主なコマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパートレードの切り替えは KABUSYS_ENV による
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレード時、settings.is_paper==True なら MockBroker を用い、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）へ記録します。
  - run_execution は data/stop_requested.flag（プロジェクトルート data/stop_requested.flag）を監視し、存在すると起動せず終了、起動後もフラグ検知で停止します。
  - 実行中は PID を data/execution.pid に書きます（PID ファイルの stale 検出は SystemMonitor が行います）。

- 監視ループ起動（SystemMonitor）
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（秒、デフォルト 60）。
  - 注意: Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用して監視ログを永続化します（監視 DB は共有されることを意図）。

- ペーパートレード検証レポート生成
  - 起動:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等の指標と PASS/FAIL 判定

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

---

## 停止・Kill Switch に関する注意

- 実行停止は複数の方法で行います。
  - data/stop_requested.flag: run_execution/run_monitoring のスクリプトが監視しているファイル。作成するとスクリプトは安全に終了します。
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に対して停止シグナルを送る用途（監視ロジックによって書き込まれる）。
- KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に kill.flag を自動クリアしますが、本番では推奨されません（安全装置を誤って無効化する可能性があるため）。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下。主なファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード・設定オブジェクト
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化 + CRUD ラッパー
    - system_monitor.py      — プロセス稼働・データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の生成 / クリア
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py       — （アラート送信機能: 実装箇所）
  - execution/                — ExecutionEngine・Order 管理関連（参照あり、詳細は別ファイル群）
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数決定・制約・丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングし ai_scores に書き込み
    - regime_detector.py     — マクロ+MA 合成による日次レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

（上記はコードベースの主要な役割を示しています。実際の全ファイルはリポジトリを参照してください。）

---

## 運用上の注意・ベストプラクティス

- .env は機密情報を含むため、決してリポジトリに含めないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にし、LINE による通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を適切に行ってください。
- ペーパートレードは本番 DB と完全分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を利用する機能は API コスト・レート制限に注意。API キーは環境変数で安全に管理してください。
- Monitoring は本番監視 DB を直接操作するため、誤って本番 DB を消去しないよう DB パス設定に注意してください。

---

## よくある操作の例

- Monitoring のポーリング間隔を 30 秒に変更して起動:
```bash
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- ペーパートレードのレポートを指定 DB で生成:
```bash
python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db --from 2026-04-01 --to 2026-04-11
```

---

質問やドキュメントの補足が必要であれば、どの箇所を詳しく知りたいか教えてください。README の改善・追記（例: 実行フロー図、設定例テンプレート、運用手順）も対応します。