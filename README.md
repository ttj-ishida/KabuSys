# KabuSys

日本株向け自動売買システムのサブセット実装ドキュメント（README）。  
このリポジトリは発注エンジン、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース評価等のコンポーネントを含みます。

> 注意: この README はコードベースのソースから自動生成した要約です。実運用前に必ず `.env` 設定や config/*.yaml を確認してください。

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は以下です。

- 発注（ExecutionEngine）とブローカークライアントの抽象化（paper_trading と live の切替）
- システム監視（CPU / メモリ / ディスク / プロセスの死活、データ鮮度）
- 取引監視（滞留注文、約定価格異常）
- リスク監視（ドローダウン、保有銘柄数上限）
- Kill Switch（リスクトリガーによる安全停止）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ（ファクター計算、将来リターン、IC 等の統計）
- ニュース NLP（OpenAI を用いたニュースセンチメント集約）
- Paper Trading 検証レポート生成ツール

設計方針の一例：
- DuckDB / SQLite をデータ層に利用
- environment （KABUSYS_ENV）により paper_trading / live / development を切替
- AI 呼び出し（OpenAI）はフェイルセーフで失敗時はフォールバック動作

## 主な機能一覧

- CLI / スクリプト
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ExecutionEngine 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper Trading レポート生成: python -m kabusys.tools.paper_verification_report

- 監視・アラート
  - SystemMonitor: CPU/MEM/DISK、プロセス死活、データ鮮度
  - TradeMonitor: 滞留注文、約定異常価格
  - RiskMonitor: ドローダウン・ポジション数の監視、ダッシュボード更新
  - KillSwitch: 危険条件で flag ファイルを書き ExecutionEngine を停止

- 発注・リスク管理
  - ExecutionEngine と OrderManager / RiskManager / Reconciler 等（実装本体は別モジュール）
  - paper_trading モードでは MockBrokerClient を使用して専用 DB（data/paper_trading.db）に記録

- ポートフォリオ構築
  - 銘柄選定（スコア順ソート）
  - 重み（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap

- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB 上の prices_daily, raw_financials を参照）
  - 将来リターン・IC・統計サマリ機能

- AI
  - news_nlp.score_news: OpenAI を使った銘柄ごとのニュースセンチメント評価（ai_scores テーブルへ）
  - regime_detector.score_regime: マクロニュース + ETF MA200 を組み合わせた市場レジーム判定

## セットアップ手順

前提
- Python 3.10+ を推奨（typing の | 型などを使用）
- SQLite は標準ライブラリ。外部パッケージ: duckdb, psutil, openai。PyYAML は設定検証で任意で使用。

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 設定検証で YAML を使う場合: pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下記の主要環境変数例参照）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit code 1）

5. データディレクトリ
   - デフォルトの DB 等は data/ 以下に置かれます。必要に応じてディレクトリ作成:
     - mkdir -p data

主要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリアするか）

config.py に各プロパティの説明があります（必読）。

## 使い方

基本的なコマンド例:

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に stop を要求する場合は stop_requested.flag を作成（run_execution と run_monitoring はこのフラグを参照）

- Monitoring 起動（監視ループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを更新
    - stop は data/stop_requested.flag を作成して行う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

AI 機能のプログラムからの呼び出し例（ニュース NLP）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 4, 10))
print("書き込み銘柄数:", written)
```

市場レジーム判定（プログラム呼び出し例）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 4, 10))
```

監視・Kill Switch の仕組み
- RiskMonitor がドローダウンやポジション上限を検出すると risk_logs に記録し、KillSwitch が条件を満たすと data/kill.flag を書き込みます。
- ExecutionEngine は kill.flag の存在をチェックして安全停止できます（設定に依存）。

停止フラグ
- data/stop_requested.flag: run_execution / run_monitoring が参照する「ソフト停止」フラグ
- data/kill.flag: KillSwitch により書き込まれる「緊急停止」フラグ
- pid ファイル: data/execution.pid（実行中プロセスの PID を記録）

プロセス優先度
- run_execution と run_monitoring は起動時に set_process_priority("high") を呼びます（psutil を利用）。権限がない場合は警告が出ます。

注意点（運用上の注意）
- KABUSYS_ENV=live の場合は取り扱い注意。validate_config は live 時に警告を表示します。
- .env は絶対に Git 管理しないこと（config_setup にも注意書きあり）。
- OpenAI 呼び出しはネットワークや料金に依存するため、テスト/本番で鍵やレート管理を適切に行ってください。
- Paper Trading は本番 DB と分離されるよう実装されています（データ分離）。

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定取得ロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（監視ログ）
    - system_monitor.py            — システム監視（CPU/MEM/DISK/データ鮮度）
    - trade_monitor.py             — 注文滞留 / 約定異常監視
    - risk_monitor.py              — ドローダウン / ポジション上限チェック
    - monitoring_engine.py         — 各モニタを束ねるエンジン
    - kill_switch.py               — kill.flag の書き込み / 管理
    - alert_manager.py             — （実装ファイルあり・省略）
  - execution/
    - （ExecutionEngine, OrderManager, BrokerFactory 等 — 本 README では参照のみ）
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み付け
    - position_sizing.py           — 株数決定、スケールダウンロジック
    - risk_adjustment.py           — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py           — momentum/value/volatility の算出（DuckDB）
    - feature_exploration.py       — 将来リターン / IC / 統計
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI）と ai_scores 書込
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
    - __init__.py

プロジェクトルート（スクリプトや .env, data ディレクトリなど）
- .env (推奨: .env.local を使う)
- data/
  - monitoring.db (SQLite, デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB デフォルトパス)
  - execution.pid
  - kill.flag
  - stop_requested.flag

## 開発者向けメモ

- DuckDB 接続は各モジュールに渡して SQL と Python を組み合わせて処理しています。
- AI 呼び出し部分（news_nlp, regime_detector）は外部 API 呼び出しを行うため、テストでは _call_openai_api を patch して差し替えることが想定されています。
- monitoring_db.init_monitoring_db は冪等でマイグレーション（カラム追加）も行います。
- config._load_env_file はプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はリポジトリ内のソースコードを基にした要約です。実運用やカスタマイズの際は各モジュール内 docstring とコードを参照し、十分なテストを実施してください。質問や補足があればお知らせください。