# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム「KabuSys」のアプリケーションコード群です。  
README は本プロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つマイクロサービス風の Python パッケージです：

- 戦略（ファクター計算 / シグナル生成 / ポートフォリオ構築）
- 実行層（ExecutionEngine） — ブローカーとのやり取り・発注管理・リスク管理
- 監視層（Monitoring） — システム状態、オーダー状況、リスク監視、Kill Switch
- 研究ツール（DuckDB を使ったファクター計算、特徴量解析）
- AI 支援機能（ニュース NLP によるセンチメント算出、レジーム判定）
- ペーパートレード用分離 DB／レポート生成ツール

設計方針として、DuckDB / SQLite を組み合わせてデータ分析・ログ永続化を行い、OpenAI（LLM）を任意で利用する拡張を想定しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録
- 監視エンジン起動スクリプト: run_monitoring.py
  - ポーリングで SystemMonitor を呼び出し、監視ログを永続化
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）
- 監視コンポーネント:
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常の検出）※実装ファイルあり
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（監視結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止信号）
  - AlertManager（外部通知を行う想定）
- ポートフォリオ構築補助（純粋関数群）
  - 候補選定、重み算出、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究ツール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI モジュール（任意）
  - news_nlp.score_news: LLM を用いた銘柄ごとのニュースセンチメント算出（ai_scores テーブル書き込み）
  - regime_detector.score_regime: マクロ＋ETF MA を使った市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレーディングの検証レポート生成

---

## 動作要件（依存関係）

最低限必要な Python パッケージ（一例）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の詳細検証を使う場合に任意で）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそちらを使用してください）

標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

---

## セットアップ手順

1. リポジトリをクローンする  
   git clone <repo-url>

2. 仮想環境を作成し依存関係をインストールする（上記参照）

3. .env を用意する  
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 自動ロード: kabusys.config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. 必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   その他（任意）: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY, PAPER_TRADING_SQLITE_PATH 等

5. 設定検証（起動前推奨）:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いします

6. データディレクトリ作成（必要に応じて）:
   defaults: data/, logs/
   例: mkdir -p data logs

---

## 使い方（起動 & 操作）

### 実行エンジン（ExecutionEngine）を起動

- 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替:

  - 開発（デフォルト）:
    export KABUSYS_ENV=development
  - ペーパートレード:
    export KABUSYS_ENV=paper_trading
  - 本番:
    export KABUSYS_ENV=live

- 起動:

  python -m kabusys.run_execution

- 動作概要:
  - Execution は Settings による環境判定で paper_trading の場合は PAPER_TRADING 用 SQLite を使用（settings.paper_sqlite_path）。
  - PID ファイル: data/execution.pid（デフォルト）
  - 停止: data/stop_requested.flag を作成すると実行スレッドが検知して安全に停止します。Kill Switch (data/kill.flag) は監視から書き込まれます。

### 監視ループを起動

- 起動:

  python -m kabusys.run_monitoring

- オプション: ポーリング間隔を環境変数で上書き
  export MONITOR_POLL_INTERVAL=30  # 秒

- 動作概要:
  - 監視は MonitoringDB（SQLite）へログを永続化します。monitoring は Settings.env に関わらず本番 sqlite_path を使用する点に注意。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループ終了

### .env の対話式作成

python -m kabusys.config_setup

ウィザード完了後、.env を保存してから validate_config で検証することを推奨します。

### 設定の検証

python -m kabusys.validate_config
python -m kabusys.validate_config --strict

### ペーパートレード検証レポート生成

- 例: 全期間（デフォルト DB パス: data/paper_trading.db）
  python -m kabusys.tools.paper_verification_report

- 例: 期間指定・DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

### AI 機能（ニュース NLP / レジーム判定）

- OpenAI API キーを用意し、環境変数 OPENAI_API_KEY を設定してください（または関数呼び出し時に api_key 引数を渡す）。
- 例（モジュール呼び出し）:

  from openai import OpenAI
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,1))

- 注意:
  - API 使用には料金が発生します。失敗耐性（リトライ、フォールバック）を備えていますが、API キーの管理は慎重に行ってください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite パス（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / ...）デフォルト: INFO
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

詳細は kabusys.config.Settings クラスのプロパティを参照してください。

---

## 停止 / Kill Switch / フラグファイルについて

- 停止要求（外部）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが安全に停止します（両スクリプトともこのファイルを監視）。
- Kill Switch:
  - 監視が致命的なリスク（例: ドローダウン超過、ポジション上限超過）を検出した場合、data/kill.flag を書き込んで ExecutionEngine に停止を促します。
  - ExecutionEngine の起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では 0 を推奨）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルとディレクトリの構成（src/kabusys 以下）です。実際のプロジェクトルートには README や pyproject.toml 等が存在します。

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / Settings
    - config_setup.py              # .env ウィザード
    - validate_config.py           # 設定検証 CLI
    - run_execution.py             # ExecutionEngine 起動スクリプト
    - run_monitoring.py            # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py                # ニュース NLP スコアリング
      - regime_detector.py         # 市場レジーム判定
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (※実装例あり)
    - execution/
      - (ExecutionEngine / OrderManager / BrokerFactory 等)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

注意: 上記はソース内の主要モジュールを抜粋した構成です。細かい実装ファイルは実際のリポジトリを参照してください。

---

## 開発上の注意点 / 運用メモ

- monitoring 側は「環境にかかわらず」本番用の sqlite_path（デフォルト data/monitoring.db）を使用する設計になっています。監視データを誤ってペーパートレード DB と混在させないよう注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 専用の SQLite を使用して完全分離します。
- ログは logs/ ディレクトリへ日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。
- プロセス優先度設定: 起動時に set_process_priority("high") を呼び出します。権限や OS によっては警告が出ますが動作継続します。
- DuckDB のバージョン差や executemany の空リスト扱いなど互換性注意点がコードコメントにあります。DuckDB のバージョンにより DB 操作の挙動が変わる可能性があります。
- AI 機能は外部 API（OpenAI）を利用するためコストとレート制限に注意。API エラーに対してはリトライとフォールバックが実装されていますが、運用上は API キーおよび課金設定を事前に確認してください。

---

必要であれば、以下も追加で作成できます:
- サンプル .env.example（必須項目を示したテンプレート）
- systemd / supervisor 用のユニットファイル例（run_execution / run_monitoring の常駐化）
- requirements.txt / constraints.txt

何か追加したいセクション（例: systemd サービス定義、データベーススキーマの詳細、開発用コマンド一覧）があれば教えてください。README に追記して整備します。