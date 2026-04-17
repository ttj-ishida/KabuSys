# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、トレード実行エンジン、監視・アラート、ポートフォリオ構築、ファクター研究、AI（ニュースセンチメント／レジーム判定）などを含むモジュール群をまとめたものです。実行環境はローカル開発 / ペーパートレード / 本番（live）を想定しています。

---

## 概要

主な役割とコンポーネント

- ExecutionEngine（実行エンジン）
  - ブローカークライアント経由で発注を管理。paper_trading モードでは MockBroker を使用して paper_trading DB に記録。
  - 依存: ブローカークライアント、OrderRepository、RiskManager、OrderManager、Reconciler 等。
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねてポーリングし、監視ログを SQLite に永続化。Kill Switch により異常時に Execution を停止可能。
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、ポジションサイジング、セクター制約などの純粋関数群。
- Research（研究）
  - DuckDB 上でファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン計算、IC 計算、統計サマリー。
- AI（ニュース NLP / レジーム判定）
  - OpenAI を使ったニュース記事のセンチメント集約（ai_scores への書き込み）や、ETF の MA200 等と組み合わせた市場レジーム判定。
- ユーティリティ
  - 環境設定（.env ウィザード）、設定検証 CLI、プロセス優先度設定ユーティリティなど。

---

## 機能一覧

- 実行モード切替（KABUSYS_ENV: development / paper_trading / live）
- 発注履歴・監視ログの永続化（SQLite）、分析用データ格納（DuckDB）
- 監視ループ（CPU/メモリ/ディスク、プロセス生存、データ鮮度、滞留注文、約定異常、ドローダウン、ポジション上限）
- Kill Switch（データ/kill.flag による Execution 停止）
- Paper Trading 検証レポート生成ツール（orders / latency / 稼働率 等の集計）
- ニュース NLP による銘柄別センチメントスコアの算出（OpenAI）
- 市場レジーム判定（ETF MA200 とマクロニュースセンチメントの合成）
- 環境設定ウィザード（.env 生成）、設定検証ツール（.env / config/*.yaml のチェック）
- ポートフォリオ組成ロジック（候補選択、等配分・スコア配分、リスクベースのサイジング、セクター制約）

---

## 前提 / 必要パッケージ

推奨 Python バージョン: 3.10+

主な外部依存（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（設定検証で任意）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

（requirements.txt は本コードベースに含まれていないため、必要に応じてプロジェクト用に作成してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化し、依存パッケージをインストール
3. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合はプロジェクトルートに `.env` を置き、必要な環境変数を設定する（下記「環境変数」を参照）
4. 設定を検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります
5. data ディレクトリなど必要ディレクトリを作成（.env のパスに応じて）
   ```
   mkdir -p data
   ```

---

## 環境変数（主要）

デフォルト値は .env ウィザードやコード内の docstring を参照してください。主な変数:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行モード
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- データベース
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY — AI モジュール利用時に必要
- ログ / 制御
  - LOG_LEVEL — DEBUG/INFO/...
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）
  - PID_FILE_PATH, KILL_FLAG_PATH — ファイルパス（デフォルトは data 配下）
- 監視間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主なコマンド）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: `MONITOR_POLL_INTERVAL=30`）
  - 監視は常に本番用の sqlite_path を使用（環境モードに依存しない）
  - 停止はプロジェクトルートの data/stop_requested.flag を書き込むことで行います

- 実行エンジン（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し `data/paper_trading.db` に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
  - 実行停止は data/stop_requested.flag を作成することでシグナル送信

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで対象 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI / レジーム判定（ライブラリ関数）
  - ニューススコア算出:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - どちらも OpenAI API キー（OPENAI_API_KEY か関数引数）が必要です

---

## 停止・制御フラグ

- data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグファイル
- data/kill.flag — KillSwitch が作成する停止フラグ（ExecutionEngine 停止用）
- data/execution.pid — ExecutionEngine が書き込む PID ファイル（SystemMonitor が生存チェックに使用）

KillSwitch の条件（例）:
- ドローダウン超過（RiskMonitor）
- ポジション数の上限超過

KillSwitch が発動すると `kill.flag` が書き込まれ、ExecutionEngine はそれを検知して停止します。

---

## 注意点 / 運用メモ

- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を使用）
- monitoring は本番の sqlite_path を常に参照する設計（環境に依存しない）
- OpenAI 呼び出しは外部 API のためリトライとフェイルセーフを組み込んでいます。API キーが未設定の場合は例外を投げます（呼び出し側でキャッチしてください）
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも警告あり）
- validate_config は PyYAML がインストールされていると config/*.yaml のパース検証も行います（無い場合は警告）

---

## ディレクトリ構成

以下は src/kabusys 配下の主要ファイルとディレクトリ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境設定読み込み / Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 監視テーブルの初期化 / 永続化クラス
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — （アラート送信処理：実装省略箇所があるかもしれません）
  - execution/
    - ...                    — Execution 側の各種コンポーネント（OrderManager 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 株数決定・投資制約・単元丸め
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（モメンタム/バリュー/ボラティリティ）
    - feature_exploration.py — IC/将来リターン/統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメントの LLM 集約ロジック
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

実際の実装ファイルは src/kabusys 以下に多数含まれます。ここでは主要なものを抜粋しました。

---

## よくあるコマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README に追記したい項目（例: 詳しい環境変数一覧、サンプル .env、データベーススキーマ図、運用手順、デバッグ方法など）があれば指示してください。README をその内容に合わせて拡張します。