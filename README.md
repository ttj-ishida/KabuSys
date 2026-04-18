# KabuSys

日本株向け自動売買 / 研究フレームワーク (KabuSys)

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジンと、それを支えるモニタリング・研究用ユーティリティ群を含む Python ベースのプロジェクトです。  
主な目的は以下です：

- 発注エンジン（ExecutionEngine）による注文管理（実運用 / ペーパートレード）
- 監視システム（System / Trade / Risk）による稼働監視と Kill Switch（停止フラグ）制御
- ポートフォリオ構築・ポジションサイジング・リスク制御の純粋関数群
- DuckDB を用いたファクター計算・研究モジュール
- OpenAI を用いたニュースセンチメント / レジーム判定の補助機能
- ペーパートレードの検証レポート生成ツール

設計方針として、発注ロジックと分析ロジックは分離され、ペーパートレード時は本番 DB と分離される（データファイル別）ようになっています。

---

## 主な機能一覧

- Execution
  - 実際のブローカー（kabuステーション）またはモックブローカーでの発注処理
  - RiskManager / OrderManager / Reconciler を組み合わせた実行エンジン
  - ペーパートレード（KABUSYS_ENV=paper_trading）の完全分離（`data/paper_trading.db`）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて停止フラグファイルを書き込み ExecutionEngine を停止
  - MonitoringEngine：上記モニタを束ねてポーリング

- Portfolio（純粋関数）
  - 候補選定、等金額/スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- Research
  - DuckDB を用いたモメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの統計ツール

- AI（OpenAI 連携）
  - ニュースの NLP センチメント評価（ai_scores テーブルへの永続化）
  - マクロニュース + ETF MA による市場レジーム判定

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report）

---

## 必要要件 / 依存パッケージ（代表例）

このリポジトリに明示的な requirements.txt は含まれていませんが、主要な依存は次の通りです：

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（config 検証時に YAML 検証を行う場合に任意）

インストール例：

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# またはローカルパッケージとしてインストールできる場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成して依存をインストール（上記参照）。

3. 環境変数の初期作成（対話式ウィザード推奨）：

```bash
python -m kabusys.config_setup
```

このウィザードはプロジェクトルートの `.env` を生成・更新します。`.env` は絶対に Git にコミットしないでください。

4. 設定検証（起動前に必ず）：

```bash
python -m kabusys.validate_config
# 警告も FAIL としたい場合:
python -m kabusys.validate_config --strict
```

5. 必要に応じて `data/` ディレクトリを作成（多くのファイルは起動時に自動作成しますが、権限等の問題がある場合は事前作成が安全です）：

```bash
mkdir -p data
```

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（`instant` | `partial` | `never` | `reject`）（デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）（default 60） — run_monitoring で利用

その他の設定は `config_setup` のウィザードや `Settings` クラスのプロパティを参照してください。

---

## 使い方（主要コマンド）

- 環境作成ウィザード（.env 生成）

```bash
python -m kabusys.config_setup
```

- 設定検証

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- 実行エンジン起動（ExecutionEngine）

```bash
python -m kabusys.run_execution
```

- 監視ループ起動（SystemMonitor をポーリング）

```bash
# MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で指定可能
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- ペーパートレード検証レポート生成

```bash
# デフォルト DB path: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# 個別 DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI モジュール（プログラム内での利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キーを `api_key` 引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。

---

## 停止 / Kill スイッチ

- 監視系・実行系はフラグファイル方式で停止信号をやり取りします：
  - data/kill.flag : KillSwitch が書き込む停止フラグ（ExecutionEngine に停止を命令）
  - data/stop_requested.flag : run_monitoring / run_execution がループを抜ける確認用フラグ
  - data/execution.pid : 実行プロセスの PID（SystemMonitor が存在確認）

- KillSwitch はリスク条件（ドローダウン、ポジション上限等）で `kill.flag` を作成し、ExecutionEngine 側が検知して安全停止します。`.env` の `KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に kill.flag を自動クリアしますが、本番 (`live`) では推奨されません。

---

## 実装上の注記（運用者向け）

- Monitoring は常に本番の sqlite_path（`SQLITE_PATH`）を使用します。監視データは環境に依らず共通の監視 DB に書き込まれます。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に履歴を記録して本番 DB と分離します。
- init_monitoring_db 関数は起動時にスキーマを冪等に作成・マイグレーションします（例: カラム追加など）。
- Process priority は起動直後に `set_process_priority("high")` を呼んで優先度を上げます（psutil を使用。権限不足時は警告でスキップ）。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主なファイル・ディレクトリです。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/                      — 発注エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py             — 監視 DB 永続化層
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
  - utils/
    - process_priority.py

（完全なファイル一覧はソースツリーを参照してください）

---

## よくある質問 / トラブルシューティング

- DuckDB / SQLite ファイルが見つからないというエラー：
  - 環境変数 `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を確認してください。
  - `python -m kabusys.validate_config` でパス周りの警告を確認してください。

- OpenAI を使うときに API キーが無い：
  - `OPENAI_API_KEY` を環境変数にセットするか、関数呼び出し時に `api_key` を渡してください。

- 実行中にプロセスがすぐ終了する / stale PID のログが出る：
  - `data/execution.pid` の内容が有効な PID であるか、または PID ファイルが残ってしまっていないか確認してください。SystemMonitor は stale PID を検出すると削除します。

---

## ライセンス / 貢献

この README に記載のコードはサンプルプロジェクトとして提供されています。実運用時は十分な検証を行い、必要に応じて監視・ロギング・エラーハンドリング・権限などを強化してください。

貢献・バグ報告は Pull Request / Issue で受け付けます。

---

必要なら README に実際のコマンドの例や .env のサンプルを追加できます。どのレベルの詳細を追加希望か教えてください。