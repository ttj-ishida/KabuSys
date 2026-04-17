# KabuSys

日本株向けの自動売買システム（ライブラリ & 実行スクリプト群）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AIベースのニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えたモジュール群です。

- ExecutionEngine（発注管理・リスク管理・再整合）
- Monitoring（プロセス／データ鮮度／注文異常／リスク監視）
- Portfolio construction（候補選定・重み付け・ポジションサイジング）
- Research（ファクター計算・特徴量解析・IC計算）
- AI モジュール（ニュースに対する LLM ベースのセンチメント、マーケットレジーム判定）
- ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

設計上の特徴：
- DuckDB（分析用）と SQLite（監視・ペーパートレード用）を併用
- Paper Trading 環境は本番 DB と完全分離（専用 SQLite を使用）
- LLM（OpenAI）呼び出しは失敗耐性とリトライを備え、安全にフォールバック
- .env ベースの環境変数管理（自動ロードを有効／無効可能）

---

## 主な機能一覧

- 実行・発注
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV により実挙動 / ペーパートレードを切替え
  - BrokerClientFactory によるブローカークライアント生成（paper_trading では Mock）

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で制御）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor をまとめて実行
  - KillSwitch: ドローダウンやポジション上限で ExecutionEngine を停止するためのフラグファイルを書く

- ポートフォリオ構築（純関数）
  - 銘柄候補選定、等重・スコア重み、セクター制限、ポジションサイズ計算（単元丸め含む）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI（OpenAI）
  - ニュース記事の銘柄別センチメント算出（ai_scores へ格納）
  - マクロニュース＋ETF MA200 乖離から市場レジーム判定（bull/neutral/bear）

- ツール
  - config_setup.py: .env 対話式ウィザード（初期作成・編集）
  - validate_config.py: 必須環境変数や config/*.yaml 等の検証 CLI
  - tools/paper_verification_report.py: ペーパートレード DB を集計して PASS/FAIL レポート生成

---

## 必要な外部ライブラリ（代表例）

少なくとも以下は必要／推奨されます：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml のパース検証を行う場合、任意）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成。代表的なキー:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能利用時)
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など

4. 設定検証（起動前推奨）:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```

5. データディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

注意:
- config_setup / validate_config はプロジェクト内の config ディレクトリや .env 例を参照します。
- 自動 .env ロードはデフォルト有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動
  - 本番 / ペーパートレードは KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレードでは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 起動時に data/execution.pid が使われます。停止は data/stop_requested.flag を作成するか、監視側が data/kill.flag を書きます。

- Monitoring を起動（常駐ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使います（環境にかかわらず）。
  - 停止は data/stop_requested.flag を作成するとループが終了します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。オプション --db で指定可能。
  - 判定基準（稼働率・成功率・送信率・P95 レイテンシ等）はツール内のしきい値で定義されています。

- AI 関連（ライブラリ利用時）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続と target_date, api_key を渡して呼び出す
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    ```

注意: AI 関数は OPENAI_API_KEY の設定（引数または環境変数）を必要とします。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア, 0=しない）

---

## 停止・Kill Switch について

- Execution の停止（外部から）
  - data/stop_requested.flag が存在すると run_execution/run_monitoring は停止・シャットダウンします。
- KillSwitch（リスク条件に応じた強制停止）
  - 監視コンポーネントが条件を満たすと data/kill.flag を書き込みます（ExecutionEngine は起動時にこのフラグを検知して起動を抑止、または実行中は監視が検出すると停止処理を呼びます）。
  - 本番で自動クリアが危険な場合は KILL_FLAG_CLEAR_ON_START を 0 にしてください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの src/kabusys 以下の主要モジュールを抜粋します。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - (発注関連コンポーネント群: Engine, OrderManager 等)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / ...）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/ (実行時に生成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト)

（上記はソースコードからの主要抜粋です。細かなファイルは実際のリポジトリ構成を参照してください）

---

## 開発者向けメモ

- DuckDB は分析用テーブル（prices_daily / raw_financials / raw_news など）を前提に実装されています。テーブルスキーマに合うデータをロードしてから AI / Research 機能を実行してください。
- process_priority.set_process_priority は psutil を利用します。権限不足で設定できない場合は警告を出してスキップします。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時に自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LLM 呼び出し部（news_nlp と regime_detector）はリトライ・バックオフ・入力検証を備え、API失敗時は安全側にフォールバックしますが、APIキー漏洩やコストに注意してください。

---

## よくあるコマンドまとめ

- 環境作成 / 依存インストール:
  - python -m venv .venv && source .venv/bin/activate && pip install duckdb psutil openai pyyaml
- .env 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加してほしい項目（例: Docker / systemd ユニット例、より詳細な .env.example、テーブルスキーマの説明、起動順序図など）があれば教えてください。README をその要望に合わせて拡張します。