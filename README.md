# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI ベースのニュース評価などを含むコンポーネント群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を備えた日本株アルゴリズム取引プラットフォームのコア実装例です。

- シグナル生成・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注エンジン（execution）とブローカークライアント抽象化
- 実行監視（monitoring）とリスク監視・Kill Switch
- AI を用いたニュースセンチメント評価（ai）
- Paper Trading 用検証レポート作成ツール（tools）
- 環境設定ウィザードと設定検証ツール（config_setup / validate_config）
- ロギング・プロセス優先度設定ユーティリティ等の共通ユーティリティ（utils）

設計方針の一例：
- DuckDB を分析用 DB、SQLite を監視・履歴用に使用
- 環境変数（.env）と Settings クラスによる設定管理
- 本番／ペーパートレードを切り替え可能（KABUSYS_ENV）
- OpenAI（gpt-4o-mini）を利用したニュース NLP モジュール（APIキー必須）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py: SystemMonitor を定期ポーリングし監視ログを保存
- 設定管理
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: .env と config/*.yaml の整合チェック
- 監視
  - monitoring/monitoring_engine.py: 各種モニタの束ね
  - monitoring/system_monitor.py: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - monitoring/trade_monitor.py, risk_monitor.py, kill_switch.py 等（リスク判定・Kill Switch）
  - monitoring/monitoring_db.py: SQLite スキーマの初期化・読み書き
- 発注・リスク
  - execution/*: ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager 等
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み計算、ポジションサイズ決定、セクター上限等
- 研究・ファクター計算
  - research/*: Momentum / Volatility / Value 等のファクター計算、IC 計算等
- AI
  - ai/news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込み
  - ai/regime_detector.py: ETF MA とマクロニュースを用いた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## 事前準備

推奨: Python 3.10+（コードは型ヒントに Python 3.10 の構文を想定）

依存ライブラリ（主要なもの）:
- duckdb
- psutil
- openai
- PyYAML （設定ファイル検証時に任意で必要）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

注意:
- requirements.txt は本リポジトリに含まれていないため、プロジェクトで必要なパッケージを適宜インストールしてください。

---

## 環境設定 (.env)

このプロジェクトは環境変数から設定を読み込みます。主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時に使用）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）

PAPER_TRADING 用:
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

Kill Switch 関連:
- KILL_FLAG_CLEAR_ON_START: 0 | 1（起動時に kill.flag を自動クリアするか）

.env の生成はウィザードを利用できます（後述）。

サンプル .env（重要: .env はコミットしないでください）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## セットアップ手順（基本）

1. リポジトリをクローンし、仮想環境を用意して依存をインストールする。
2. .env を作成する:
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成。
3. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。
4. 必要に応じて data/ ディレクトリを作成（実行時に自動作成される箇所もありますが、権限に注意）。
5. ログディレクトリ（デフォルト: logs/）が作成されるか確認。

---

## 実行方法

- ExecutionEngine（発注エンジン）起動:
  ```bash
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中に data/stop_requested.flag（スクリプトルートの data/stop_requested.flag）を作成するとエンジンに停止シグナルを送れます。
  - プロセス優先度を high に設定します（psutil により一部 OS で動作しない場合あり）。
  - 実行時に PID が data/execution.pid に書かれます（設定により変更可）。

- Monitoring（監視ループ）起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  挙動:
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）。

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラムから呼ぶ）:
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

  注意: OpenAI API を使用する関数は api_key または環境変数 OPENAI_API_KEY が必要。

---

## ログとファイル配置（デフォルト）

- ログ: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - ローテーション: 日次、30世代保持
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御
- SQLite（監視）: data/monitoring.db（SQLITE_PATH）
- DuckDB（分析）: data/kabusys.duckdb（DUCKDB_PATH）
- Paper Trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（監視 / 実行ループの停止用）
  - data/kill.flag（Kill Switch が発動したときに作成される）

---

## 注意事項 / 運用メモ

- KABUSYS_ENV の設定:
  - development: 開発向け（発注なしで安全に動作するよう実装箇所あり）
  - paper_trading: 発注ロジックはモックに差し替わり、paper DB に記録
  - live: 本番。外部 API キー等の管理に注意
- Kill Switch:
  - リスク条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止する仕組みがあります。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、危険な設定なので注意。
- DB スキーマの互換性:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成および簡単なマイグレーションを実行します。
- OpenAI の呼び出し:
  - rate limit・ネットワーク障害・5xx はリトライ戦略を実装していますが、APIコストや利用制限に注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 設定読み込み / Settings
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite 永続化（監視用）
    - monitoring_engine.py         — 複数 Monitor を束ねるエンジン
    - system_monitor.py            — システム状態・データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション監視
    - kill_switch.py               — Kill Switch ロジック
    - alert_manager.py             — （アラート送信の管理：LINE 等）（ファイル内参照あり）
    - trade_monitor.py             — 発注ログ/約定監視（ファイル参照あり）
  - execution/                      — ExecutionEngine / OrderManager / BrokerFactory 等
  - portfolio/                      — ポートフォリオ構築（builder / sizing / risk_adjustment）
  - research/                       — ファクター計算 / 特徴量解析
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度・CPU affinity
  - data/                           — ランタイム生成: DB やフラグファイルを置く（git 管理外推奨）
  - config/                         — 各種 YAML 設定ファイル（system_config.yaml 等）

---

## 開発者向け補足

- テスト用に Settings の自動 .env ロードを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログ出力は標準出力（StreamHandler）と日次ローテートファイルの両方に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- Process priority / CPU affinity の設定は OS により動作が異なります。権限不足で設定できない場合は警告が出ますが動作自体は継続します。
- DuckDB の接続は分析用途向けに用意されており、research モジュールは SQL と Python を組み合わせて高速に集計を行います。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 発注エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて、README に追記したい箇所（例: 詳細な設定項目、実行例、ブローカープラグインの作り方、テスト方法など）を教えてください。