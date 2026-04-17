# KabuSys

日本株向けの自動売買・リサーチ向けユーティリティ群をまとめた軽量フレームワークです。  
主な目的は以下の通りです：

- 日次のファクター計算・リサーチ（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- ExecutionEngine（発注・リスク管理）とそれを監視する Monitoring
- Paper Trading（本番と分離した模擬発注）や検証レポート生成
- ニュースを LLM でスコア化する AI モジュール（OpenAI）

バージョン: 0.1.0

---

## 主な機能

- 環境依存設定の簡易ウィザード（.env 作成 / 更新）
- 起動前設定検証ツール（env / config YAML のチェック）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- Monitoring（System / Trade / Risk モニタ）と Kill Switch（停止フラグ）
- ポートフォリオ構築ユーティリティ（候補選定・重み・ポジションサイズ）
- ファクター計算・特徴量探索（DuckDB を用いた純粋関数実装）
- News NLP（OpenAI を使った銘柄別ニュースセンチメント評価）
- Paper Trading 検証レポート生成ツール

---

## 必要条件（例）

- Python 3.9+
- DuckDB (`duckdb` Python パッケージ)
- psutil
- requests
- openai
- PyYAML（設定ファイル検証であると便利）

（requirements.txt はこのリポジトリに含まれていない想定のため、上記を pip でインストールしてください）

例:
pip install duckdb psutil requests openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（.env.example を参考にする）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正してから続行

注意:
- `.env` は絶対に Git にコミットしないでください（機密情報を含む）。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に行ってください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要なオプション環境変数
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、default: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュールを利用する場合）
- PAPER_FILL_MODE（paper_trading 時の fill 動作: instant|partial|never|reject）

---

## 使い方（主要コマンド）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/execution.pid が作成され、停止は監視側の kill.flag などで制御されます。

- Monitoring を起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを残します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連（プログラムから呼び出す形）
  - kabusys.ai.score_news を使用して raw_news を LLM でスコア化します（OpenAI API キーが必要）。
  - kabusys.ai.regime_detector.score_regime で市場レジーム判定を行い market_regime テーブルへ書き込みます。

停止方法・Kill Switch
- Kill Switch は監視コンポーネントが条件を満たした場合に data/kill.flag を書き込みます。  
- 明示的に監視ループやエンジンを停止したい場合は data/stop_requested.flag を作成すると、run_monitoring / run_execution のループが検知して終了します。

ログレベル
- LOG_LEVEL 環境変数でログレベルを設定できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 設定の流れ（推奨）

1. python -m kabusys.config_setup で .env を作成
2. python -m kabusys.validate_config で設定確認
3. 必要に応じて DuckDB/SQLite のディレクトリ（data/ 等）を作成
4. python -m kabusys.run_monitoring を起動して監視が正常に DB に書き込まれることを確認
5. python -m kabusys.run_execution を起動（まずは KABUSYS_ENV=development / paper_trading でテスト）

---

## 主要ファイルとディレクトリ構成

リポジトリは src/kabusys 以下に主要なモジュールを配置しています。主な構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを OpenAI でセンチメント評価し ai_scores に書き込み
    - regime_detector.py     — ETF MA + マクロニュースで市場レジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite を使った監視ログ永続化層
    - system_monitor.py      — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・約定異常の監視
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag の作成 / 判定ロジック
    - alert_manager.py       — LINE push による通知（クールダウン管理）
    - monitoring_engine.py   — 監視コンポーネントの束ねとポーリング

  - execution/                — 発注・注文管理・リスク管理等（詳細実装は repository に依存）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み算出
    - position_sizing.py      — 発注株数計算・スケーリング・単元丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - process_priority.py     — プロセス優先度・CPU affinity 設定ユーティリティ

- data/                      — 実行時に使用されるデータフォルダ（DB・PID・フラグ）
  - monitoring.db (SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag

（上記はコードベースと docstring から抜粋した主要構成です。実際のファイルは更に存在する場合があります）

---

## 注意点・運用上のヒント

- 本番運用時は KABUSYS_ENV=live の設定に注意（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。
- .env に機密情報（トークン・パスワード）を含むため、決して VCS にコミットしないでください。
- OpenAI を使うモジュールは API 使用料がかかります。テストは少量データで行ってください。
- psutil による優先度設定や CPU affinity は権限によって失敗することがあるため、ログの警告に従ってください。
- DuckDB / SQLite のパス・親ディレクトリが存在しない場合、自動作成されないケースがあるため事前に data/ ディレクトリを作成しておくと良いです。

---

もし README に追加してほしい項目（例: 実際の ExecutionEngine の設定例、YAML 設定のスキーマ、詳細な API 使用例など）があれば教えてください。必要に応じてサンプル .env テンプレートや実行例を追加します。