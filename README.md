# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ & 起動スクリプト群）。  
本リポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース/NLP）などの主要コンポーネントを含みます。

> 注意: この README はソースコード（src/kabusys）に基づいて作成しています。実行に必要な外部モジュールや環境変数はプロジェクト固有です。実運用では .env を適切に設定し、テスト環境で十分に動作確認を行ってください。

---

## プロジェクト概要

KabuSys は次の責務を持つモジュール群で構成されています。

- ExecutionEngine（発注・注文管理・リスク管理） — run_execution.py から起動
- Monitoring（システム監視・取引監視・リスク監視・Kill Switch） — run_monitoring.py から起動
- Portfolio construction（銘柄選定、配分、ポジションサイジング）
- Research（ファクター計算、特徴量探索、将来リターン・IC 計算）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ツール（ペーパートレード結果検証レポート生成など）
- 設定管理（.env の対話式ウィザード / 設定検証 CLI）
- 共通ユーティリティ（ログ設定、プロセス優先度制御 等）

設計方針の特徴：
- DuckDB / SQLite を用いた分析・永続化（本番と paper_trading 用 DB を分離）
- OpenAI を利用したニュース NLP / レジーム判定（キー必須、フォールバックロジックあり）
- 自動実行スクリプトはフラグファイル（data/kill.flag、data/stop_requested.flag 等）で外部停止を制御
- .env による設定管理、対話式ウィザードと検証ツールあり

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading モードが有効）
  - python -m kabusys.run_monitoring: SystemMonitor を起動（ポーリング監視）
- 設定関連
  - python -m kabusys.config_setup: .env を対話式に生成 / 更新
  - python -m kabusys.validate_config: 起動前の設定検証（--strict オプションあり）
- 監視
  - system_monitor, trade_monitor, risk_monitor を束ねる MonitoringEngine
  - kill_switch による停止フラグ書き込み（画面/通知などにより ExecutionEngine を停止）
  - monitoring_db: 監視ログ・トレードログ・ポジション等の永続化（SQLite）
- ポートフォリオ構築
  - 候補選定、等配分/スコア配分、スコア正規化、セクター上限適用、レジーム乗数、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - ニュース記事を GPT 系モデルでセンチメント評価し ai_scores に書き込む（kabusys.ai.score_news）
  - レジーム判定（ETF MA 乖離 + マクロニュースセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提・必須パッケージ

（実行環境に応じてバージョンを調整してください）

- Python 3.10+（union 型記法 `X | Y` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を行う場合）
- SQLite（Python 標準ライブラリに同梱）

requirements.txt が用意されている場合はそれを利用してください。なければ手動でインストールします:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業ディレクトリへ移動

2. 仮想環境を作成して有効化（上記参照）

3. 必要パッケージをインストール

4. .env を作成
   - 対話式ウィザードを利用:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成された .env に必須項目が含まれていることを確認（主な必須環境変数は下記参照）

5. 設定検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   # 厳格モード（警告も FAIL）
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ/ログディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` と `logs/` が使用されます。起動スクリプトは必要なら自動で親ディレクトリを作成しますが、権限等に注意してください。

---

## 必須 / 代表的な環境変数

（.env に設定する例）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を利用する機能（news_nlp, regime_detector）に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

.env の雛形は config_setup が生成します。重要なセキュリティ注意: .env は絶対に Git にコミットしないでください。

---

## 使い方（主要スクリプト・関数）

- 起動前に kill flag をクリアしたい場合（Settings.kill_flag_clear_on_start を参照）

- 実行エンジン（ExecutionEngine）を起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、paper_trading 用 DB に記録されます。
  - 停止は data/stop_requested.flag を作成するか、kill flag (data/kill.flag) を書き込んでください。

- 監視ループを起動（SystemMonitor）:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用（環境に依らず）します。

- .env を対話式で作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定を検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポートを作る:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコア（ニュース）を実行（ライブラリ関数）:
  - Python から:
    ```py
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```

- レジーム判定:
  - score_regime 関数を直接使用可能（kabusys.ai.regime_detector 内）。OpenAI API キーが必要。

ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリ）。コンソール出力は stdout に行われます。

---

## 停止・Kill Switch の仕組み

- 外部から ExecutionEngine を安全に停止するには `data/kill.flag` を書き込む（KillSwitch が監視している場合、条件に応じて監視から自動作成することもある）。
- run_execution と run_monitoring は `data/stop_requested.flag` を検知するとループを抜けて終了します（手動停止用）。
- run_execution は起動時に既に stop flag がある場合は起動しません。

---

## ディレクトリ構成（src 以下の主要ファイル）

以下はソースツリーの要約です（主要ファイル・モジュールのみ抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス（.env 自動読み込み含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （存在する想定）トレード監視ロジック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - alert_manager.py       — （参照されているがここに含まれる想定）
  - execution/                — ExecutionEngine 周りのモジュール群（OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
    - __init__.py
  - data/                    — データファイル（実行時に data/*.db やフラグファイルを作成）

（注）一部ファイルはここに抜粋されていない補助モジュールや参照先が存在します。実行時には依存ファイル・設定をプロジェクトルート配下に配置してください。

---

## 開発上の注意点 / ベストプラクティス

- .env は絶対に VCS にコミットしない（config_setup が警告メッセージを出力します）。
- 本番（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険なので無効化推奨。
- OpenAI を使う機能は API 呼び出し失敗時にフォールバックロジックを持ちますが、料金やレート制限に注意してください。
- Paper Trading と本番 DB は分離されます。paper_trading モードで本番 DB に誤って書き込まないよう設定を確認してください。
- ログはデフォルトで logs/ に保存されます。ディレクトリ作成に失敗するとコンソールのみの出力になります。

---

## よくある操作コマンド（まとめ）

- .env を作成 / 編集:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 監視を起動:
  ```bash
  MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  ```
- エンジンを起動:
  ```bash
  python -m kabusys.run_execution
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- AI スコア（スクリプトから）:
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 1), api_key="your_openai_api_key")
  ```

---

この README はコードベースの現状に基づいた概要です。実際のデプロイや運用には運用手順書、監視・バックアップ方針、秘密情報管理（Vault 等）を併せて用意してください。問題や追加のドキュメント化が必要であれば教えてください。