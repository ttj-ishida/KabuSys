# KabuSys

日本株自動売買システム用のコアライブラリ群と実行/監視ユーティリティ群です。本リポジトリはトレードエンジン、監視エンジン、ポートフォリオ構築、リサーチ、AI支援（ニュース/NLP・レジーム判定）などを含みます。

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したアプリケーションのコア実装です。設計方針は以下の通りです。

- 実行エンジン（ExecutionEngine）と監視（Monitoring）を分離して安全に運用できる構成
- Paper Trading（ペーパートレード）と Live（本番）を環境変数で切り替え
- DuckDB を用いたリサーチ／ファクター計算、SQLite を用いた監視ログ保存
- OpenAI（GPT）を利用したニュースセンチメント / マクロ判定機能（任意）
- 設定ウィザード / 設定検証ツールを提供し起動前チェックを容易に

---

## 主な機能一覧

- 実行（run_execution.py）
  - Broker クライアントの切替（KABUSYS_ENV=paper_trading の場合はモック）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動
  - paper_trading は本番 DB と切り離された SQLite を利用

- 監視（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、監視ログを保存
  - Kill Switch（データに基づく自動停止）やアラート送信呼び出しが可能
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔変更可（デフォルト 60 秒）

- 設定支援
  - config_setup.py: 対話式に .env を作成/更新
  - validate_config.py: 起動前に環境変数や config/*.yaml を検証

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算、セクター制限、ポジションサイズ計算等

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI 機能（kabusys.ai）
  - news_nlp: ニュースを LLM でスコア化して ai_scores テーブルへ格納
  - regime_detector: ETF の MA とマクロニュースの LLM 判定を組み合わせて市場レジームを算出

- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity のユーティリティ
  - monitoring_db: SQLite を使った監視データの永続化レイヤ

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート生成

---

## 前提 / 必須要件

- Python 3.9+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル YAML 検証を行う場合）
- ネットワーク（kabuステーション API / J-Quants / OpenAI を使う場合）
- SQLite / DuckDB ファイルはデフォルトで `data/` 配下に作成されます

（パッケージ一覧はプロジェクトに requirements.txt があればそれを使用してください。なければ上記をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動

2. 仮想環境を作成・アクティベート（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （OpenAI / PyYAML は必要な機能に応じて省略可能）

4. .env の作成
   - 対話式: python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - その他: KABUSYS_ENV（development / paper_trading / live）、DUCKDB_PATH 等

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 必要なら: python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 主要な環境変数

必須（少なくとも設定ファイルに準備しておく）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション（代表例）

- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録する
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY — OpenAI を使うモジュールが参照する API キー
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — プロセス制御用の設定

注意:
- Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用する実装箇所があります（run_monitoring.py 内の挙動を確認してください）。
- paper_trading は本番 DB と完全に分離されることを意図しています（run_execution.py が paper_sqlite_path を使用）。

---

## 使い方（コマンド例）

プロジェクトルート（pyproject.toml / .git がある場所）で実行してください。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にするとペーパートレード専用 DB と Mock Broker を使用

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（例: MONITOR_POLL_INTERVAL=120）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None) など（OpenAI API キーが必要）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 運用に関する注意

- プロセス優先度
  - 起動時に set_process_priority("high") が呼ばれます。psutil の権限や OS により失敗する場合があります（警告ログのみ）。
- 停止フラグ / Kill Switch
  - プロジェクト内の `data/stop_requested.flag`（run scripts が使用）や `.env` で指定した KILL_FLAG_PATH（KillSwitch 用）を介してエンジンを安全に停止できます。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動クリアされるため）。
- PID ファイル
  - 実行エンジンは PID ファイル（デフォルト data/execution.pid）を使用し、SystemMonitor はその PID を確認してプロセス健全性を判断します。
- Paper Trading
  - ペーパートレード時は paper_sqlite_path（デフォルト data/paper_trading.db）へログが保存されるため、本番 DB と混在しません。

---

## トラブルシューティング（よくある問題）

- 必須環境変数未設定
  - validate_config.py で事前チェックを行ってください。起動時に Settings は必須変数未設定で例外を送出します。

- OpenAI 呼び出し失敗
  - OPENAI_API_KEY を設定してください。API エラー時はリトライ/フォールバックの実装がありますが、キー未設定だと例外になります。

- psutil による優先度設定失敗
  - 権限が不足している場合は警告ログが出て処理は継続します。sudo 等で権限を与えるか、そのまま運用してください。

- DuckDB / SQLite ファイルパスの親ディレクトリがない
  - validate_config.py は親ディレクトリの存在を警告します。起動時に自動作成されるケースがありますが、事前に `mkdir -p data` を推奨します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みユーティリティ（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py    — 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 用永続化レイヤ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - alert_manager.py       — （アラート送信の抽象化。実装ファイル参照）

  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig / run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - order_record.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - data/
    - pipeline.py             — データ取込み / get_last_price_date など
    - stats.py                — Zスコア等統計ユーティリティ

  - tools/
    - paper_verification_report.py

  - utils/
    - process_priority.py

（上記は抜粋です。詳細はソースツリーを参照してください。）

---

## 開発者向けメモ

- 自動的に .env をロードする仕組みがあります（project root に .git または pyproject.toml があることが前提）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続はモジュール内で直接 SQL を発行して集計します。テスト時は DuckDB の接続オブジェクトを注入してユニットテストを行いやすい設計が意識されています。
- OpenAI 呼び出し部分は外部から差し替え（モック）しやすいように内部呼び出し関数を定義してあります（ユニットテストで patch 可能）。

---

## 参考コマンド例（まとめ）

- 仮想環境作成・依存インストール
  - python -m venv .venv && source .venv/bin/activate
  - pip install duckdb psutil openai PyYAML

- .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- 実行エンジン（paper_trading 例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ（ポーリング間隔 120 秒に設定）
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring

- ペーパートレード検証レポート（DB 指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

README に書かれている内容で不明点や追加で説明が必要な箇所があれば教えてください。運用フローや具体的な起動スクリプト（systemd / supervisor / Docker など）向けのドキュメント作成も支援できます。