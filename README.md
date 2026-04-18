# KabuSys

日本株自動売買システムのコアライブラリと起動スクリプト群。  
このリポジトリは戦略・ポートフォリオ構築、発注実行、監視、AI を用いたニュース評価やレジーム判定などの機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤（研究→本番ワークフロー）を提供します。主な役割:

- ファクター計算・特徴量探索（research）
- ポートフォリオ構築・銘柄選定（portfolio）
- 発注エンジン / 注文管理（execution）
- システム・取引の監視と Kill Switch（monitoring）
- ニュースの NLP スコアリングや市場レジーム判定（ai）
- 研究用ツール（tools）や設定ウィザード（config_setup）など

設計方針の一部:
- DuckDB / SQLite をデータ層に利用（分析用に DuckDB、監視・注文ログに SQLite）
- 実行環境（KABUSYS_ENV）により paper_trading と live を分離
- OpenAI（gpt-4o-mini）を利用した NLP コンポーネント（環境変数 OPENAI_API_KEY が必要）
- フラグファイルによるプロセス停止や検証用 CLI を提供

---

## 主な機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials からファクターを計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析・IC 計算
- portfolio
  - 銘柄候補選定、等重・スコア重み、リスク調整（セクター上限）、単元丸めを含む株数計算
- execution
  - BrokerClient 経由の発注、OrderManager、RiskManager、Reconciler、ExecutionEngine（起動スクリプトあり）
  - paper_trading モードでは MockBrokerClient と専用 DB（data/paper_trading.db）を使用
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor の結合（MonitoringEngine）
  - 監視ログを SQLite に永続化（monitoring_db）
  - KillSwitch による停止フラグ生成（data/kill.flag）
  - run_monitoring 起動スクリプトで定期ポーリング
- ai
  - news_nlp.score_news：OpenAI でニュースを銘柄ごとにセンチメント評価し ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF の MA とマクロニュースの LLM 評価を合成して market_regime を算出
- tools
  - paper_verification_report：Paper Trading の検証レポート生成スクリプト
- 設定ユーティリティ
  - config_setup（対話式 .env 作成ウィザード）
  - validate_config（環境変数・config/*.yaml の事前検証）

---

## 動作環境・依存

- Python >= 3.10（型アノテーションで `X | Y` を使用しているため）
- 主な外部パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（validate_config の YAML 検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, argparse など

インストール例（仮の requirements がない場合の例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（.env）

設定は環境変数またはリポジトリルートの `.env` / `.env.local` から読み込まれます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（抜粋）:
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY （ai モジュール使用時に必須）
- ログ
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- 監視 / Kill Switch
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1、デフォルト: 0）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

対話式で .env を作る:
```bash
python -m kabusys.config_setup
```

生成例（抜粋）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

設定検証:
```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにする:
python -m kabusys.validate_config --strict
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して activate
3. 依存パッケージをインストール（上記参照）
4. 対話式ウィザードで .env を作成:
   ```
   python -m kabusys.config_setup
   ```
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
6. 必要に応じて data/ ディレクトリや DuckDB / SQLite DB ファイルを準備（自動生成される場合もあります）

---

## 実行方法

起動スクリプトはモジュールとして実行します。

- ExecutionEngine 起動（通常は本番 or paper_trading モードに依存）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 起動前に data/stop_requested.flag が存在する場合は起動を行いません。
  - 実行中は data/execution.pid が使用されます。

- Monitoring 起動（ポーリング監視）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）。
  - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV にかかわらず）。
  - 停止するには data/stop_requested.flag を作成（または Ctrl+C）。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で指定可）

AI 関連（プログラム内 API 呼び出し例）:
- 環境変数 OPENAI_API_KEY を設定しておく必要があります。
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を与えて呼び出します（スクリプトの CLI は未提供。ライブラリ関数として利用）。

停止・Kill Switch:
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。  
- ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag をクリアする挙動があります（本番では 0 を推奨）。

ログ:
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）。
- コンソール出力は stdout に送られます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可能。

---

## 主要スクリプト一覧（ショートガイド）

- python -m kabusys.config_setup
  - .env を対話式で作成・更新
- python -m kabusys.validate_config
  - 環境変数 / config/*.yaml の事前検証
- python -m kabusys.run_execution
  - ExecutionEngine を起動
- python -m kabusys.run_monitoring
  - System / Trade / Risk の監視ループを起動
- python -m kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート出力

---

## ディレクトリ構成（抜粋）

以下はソース内の主要ファイル・ディレクトリを抜粋した構成例です。

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ config_setup.py
   ├─ validate_config.py
   ├─ run_execution.py
   ├─ run_monitoring.py
   ├─ utils/
   │  ├─ __init__.py
   │  ├─ logging_setup.py
   │  └─ process_priority.py
   ├─ monitoring/
   │  ├─ monitoring_db.py
   │  ├─ system_monitor.py
   │  ├─ trade_monitor.py
   │  ├─ risk_monitor.py
   │  ├─ monitoring_engine.py
   │  ├─ kill_switch.py
   │  └─ alert_manager.py
   ├─ execution/
   │  ├─ execution_engine.py
   │  ├─ order_manager.py
   │  ├─ order_repository.py
   │  ├─ broker_factory.py
   │  └─ reconciler.py
   ├─ portfolio/
   │  ├─ portfolio_builder.py
   │  ├─ position_sizing.py
   │  └─ risk_adjustment.py
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ ai/
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   └─ tools/
      └─ paper_verification_report.py

config/
  ├─ system_config.yaml
  ├─ strategy_config.yaml
  └─ ... (生成や編集が必要)

data/
  ├─ monitoring.db (SQLite デフォルト)
  ├─ paper_trading.db (paper_trading 用)
  ├─ stop_requested.flag
  ├─ kill.flag
  └─ execution.pid

logs/
  └─ execution.log, monitoring.log, ...
```

---

## 開発上の注意点・補足

- Python バージョンは 3.10 以上を想定しています（型ヒントで `X | Y` 構文を使用）。
- OpenAI 関連の機能は API 呼び出しを行うため、利用時は API キー（OPENAI_API_KEY）を設定してください。
- Paper trading モードは本番 DB と完全に分離してデータを記録するよう設計されています（PAPER_TRADING_SQLITE_PATH を参照）。
- validate_config は YAML パーサー（PyYAML）がインストールされていない場合は YAML 検証をスキップして警告を出します。
- 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL（秒）で調整できます。無効な値を与えるとデフォルト 60 秒にフォールバックします。

---

必要であれば、README に含めるサンプル .env の完全テンプレートや、より詳細な運用手順（systemd ユニットファイル例、Docker 化手順、DB 初期化スクリプトなど）も作成します。どの情報を追記しますか？