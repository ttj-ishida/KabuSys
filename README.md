# KabuSys README

このリポジトリは日本株向けの自動売買・リサーチ基盤「KabuSys」の一部です。  
以下はコードベースの主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリ群と運用用ユーティリティを含みます。主な目的は以下です。

- 戦略・ファクター計算（DuckDB ベース）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- 実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 切替）
- 監視（System / Trade / Risk）と Kill Switch による停止制御
- AI（OpenAI）を使ったニュース NLP / レジーム判定
- ペーパートレード検証レポート生成

設計方針としては、DB（SQLite / DuckDB）をデータ永続化に利用し、LLM 呼び出しや外部 API は明示的に分離してフェイルセーフを置いてあります。

---

## 主な機能一覧

- 環境設定ウィザード（`.env` 作成補助）
- 設定検証 CLI（必須環境変数や config/*.yaml のチェック）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- Monitoring 起動スクリプト（SystemMonitor のポーリング）
- MonitoringDB（SQLite）を用いた監視ログの永続化
- RiskMonitor（ドローダウン・ポジション上限監視）と KillSwitch（停止フラグ）
- AI モジュール：
  - news_nlp: ニュースのセンチメントを OpenAI で評価して ai_scores に格納
  - regime_detector: マクロニュース + ETF MA200 による市場レジーム判定
- Research モジュール：ファクター計算（momentum / volatility / value）や統計解析（IC 等）
- Portfolio モジュール：候補選定・重み算出・ポジションサイズ計算
- ユーティリティ：ロギング設定、プロセス優先度設定、レポート生成ツール（paper_verification_report）

---

## 前提（推奨）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config/*.yaml の検証を行う場合)
- ローカルで動かす場合は SQLite / DuckDB ファイルへの書き込み権限

（requirements.txt は本リポジトリに含まれていない場合があるので、上記パッケージを手動で入れてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. レポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. 環境変数設定
   - プロジェクトルートに `.env` を作成します。手動で編集してもよいですが、対話式ウィザードが用意されています。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション（よく使うものとデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を利用する場合
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアする（0/1、デフォルト 0）
4. `.env` の作成（推奨: ウィザード）
```
python -m kabusys.config_setup
```
5. 設定の検証
```
python -m kabusys.validate_config
# 警告も厳格に扱う場合:
python -m kabusys.validate_config --strict
```

---

## 使い方（実行方法）

基本的にモジュールはパッケージとして実行できます（各スクリプトのモジュール名は下記参照）。

- 監視ループ起動（SystemMonitor のポーリング）
```
python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
補足:
- 監視は常に「本番の sqlite_path」を使用します（Settings.sqlite_path）: monitoring は KABUSYS_ENV に依らず production DB パスで動きます。
- 停止にはプロジェクトルート下の `data/stop_requested.flag` を作成して検知させます（run_monitoring, run_execution が参照）。

- 実行エンジン起動（ExecutionEngine）
```
python -m kabusys.run_execution
```
補足:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）へ記録し、本番 DB と切り離します。
- 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
- 実行中のプロセス情報は `data/execution.pid` に記録されます。

- 環境設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
```

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db オプションで別 DB を指定可能:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - モジュール API（例）
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止と Kill Switch

- ExecutionEngine や Monitoring の停止トリガー:
  - `data/stop_requested.flag`：run scripts が監視し、存在するとループを停止します（外部プロセスがこのファイルを作成して停止指示を出す想定）。
  - `data/kill.flag`：KillSwitch が書き込むファイル。ドローダウンやポジション上限等の重大アラート発生時に ExecutionEngine を停止させるために使用します。
- `KILL_FLAG_CLEAR_ON_START` を 1 にすると起動時に kill.flag を自動クリアします（本番環境では危険なので 0 推奨）。

---

## ログ

- ログはデフォルトで `logs/` ディレクトリに出力され、日次ローテーション（30日分保持）が設定されています（kabusys.utils.logging_setup）。
- コンソール（stdout）への出力も行われます。
- ログレベルは `LOG_LEVEL` 環境変数または読み込んだ `.env` で指定できます（例: DEBUG/INFO/WARNING）。

---

## 主要環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
- DB パス:
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- その他:
  - LOG_LEVEL — default: INFO
  - OPENAI_API_KEY — OpenAI を使う場合
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default 60）
  - KILL_FLAG_CLEAR_ON_START — 0/1（default 0）

詳細は `src/kabusys/config.py` を参照してください。

---

## 開発用ユーティリティ

- `kabusys.config_setup`：.env を対話式に作成
- `kabusys.validate_config`：必須環境変数や config/*.yaml の存在・パース検証
- `kabusys.tools.paper_verification_report`：ペーパートレードの期間別検証レポート生成

---

## ディレクトリ構成

主要なソース構成は以下の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB レイヤ
    - system_monitor.py
    - trade_monitor.py         — (存在する想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — (存在する想定)
  - execution/
    - execution_engine.py      — (存在する想定)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

プロジェクトルート（想定）:
- data/               — SQLite / PID / flag ファイル（実行時に作成）
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/               — ログ出力先
- config/             — YAML 設定テンプレート（system_config.yaml 等）
- src/                — Python パッケージソース

---

## 注意事項 / 運用上のヒント

- `.env` は絶対にリポジトリにコミットしないでください（シークレット含む）。
- 本番（KABUSYS_ENV=live）で動かす際は LINE 通知や Kill Switch 設定等を必ず確認してください（validate_config にてライブ向け警告あり）。
- ai モジュールは OpenAI への API 呼び出しを行うため、API キーの管理・レート制限・コストに注意してください。
- Monitoring はデフォルトで本番用 sqlite_path を参照します（監視データの分離に注意）。

---

以上がこのコードベースの概要と運用ガイドです。  
より詳細な実装や設計の意図は各モジュールの docstring / ソース内コメントを参照してください。必要であれば README を補足（例: 実行例、設定例の追加）します。