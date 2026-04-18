# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含む統合システムです。

> バージョン: 0.1.0（src/kabusys/__init__.py）

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / インストール
- セットアップ手順
- 使い方（実行コマンド）
- 主要設定（環境変数）
- 終了・停止方法（フラグファイル）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けライブラリ／アプリ群です。  
主な目的は次の通りです。

- データ基盤（DuckDB / SQLite）を利用したファクター計算・リサーチ
- シグナルに基づくポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 実行エンジン（ExecutionEngine）による発注管理（paper_trading と live をサポート）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）による常時監視と Kill Switch
- ニュースの NPL（OpenAI を利用）によるセンチメント評価とレジーム判定
- ペーパートレード検証レポート生成ツール

設計上の特色:
- 環境変数 / .env を使った設定管理（対話式の config_setup、検証用 validate_config）
- DuckDB を分析用に、SQLite を監視/発注ログ用に利用
- Paper Trading モードでは本番 DB と分離された専用 SQLite（デフォルト: data/paper_trading.db）
- OpenAI を使った NLP 部分は API キー必須（モデル: gpt-4o-mini を想定）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動スクリプト（本番 / ペーパートレード切替）
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
- portfolio: 候補選定、重み計算、位置付け（position sizing）、セクター制限、レジーム乗数
- research: ファクター計算（モメンタム / ボラティリティ / バリュー）、特徴量解析ユーティリティ
- ai: news_nlp（ニュースセンチメント） / regime_detector（市場レジーム判定）
- utils: ログ設定、プロセス優先度（nice/priority）ユーティリティ
- tools/paper_verification_report.py: ペーパートレード検証レポート出力
- config_setup.py: .env 対話ウィザード（初期作成）
- validate_config.py: 設定検証 CLI（必須 env のチェック・config/*.yaml の存在チェック）

---

## 必要条件 / インストール

推奨: Python 3.9+（コードは型ヒント等を使用）

必要な主要パッケージ（最低限）:
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の内容検証に必要、必須ではない）

例（venv を使ったインストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境作成・有効化、依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使用:
     ```
     python -m kabusys.config_setup
     ```
   - または .env.example を参考に `.env` を手動作成
4. 設定検証（任意）:
   ```
   python -m kabusys.validate_config
   # 警告もエラー化する strict モード
   python -m kabusys.validate_config --strict
   ```
5. デフォルトのデータディレクトリ（例: data/、logs/）を確認。必要なら作成されますが権限に注意。

重要:
- .env は Git にコミットしないでください（config_setup のヘッダーにも注意書きあり）。
- 自動で .env をロードする仕組みがあり、プロジェクトルートが検出されると .env / .env.local を読み込みます。テスト等で自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（主要コマンド）

- ExecutionEngine（発注エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（ペーパートレード）を使用し、paper_trading 用 DB（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中は data/execution.pid に PID を書きます（設定によりパス変更可）。

- Monitoring 起動（SystemMonitor のポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を利用する仕様です（環境に関わらず）。

- 設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（手動呼び出し、コード API）:
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キー必要
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — OpenAI API キー必要

---

## 主要設定（環境変数）

一部抜粋（全ては config_setup または config.py を確認してください）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション:
- KABUSYS_ENV — 実行環境（development, paper_trading, live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モード）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（ai.news_nlp / ai.regime_detector）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）

自動読み込みの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

ログ:
- デフォルトログディレクトリ: logs/
- setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）に出力

---

## 終了・停止方法（フラグファイル）

このプロジェクトではフラグファイル経由の停止制御を採用しています。

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py はこのファイル存在をチェックして停止・起動中止します。
  - 手動停止: このファイルをプロジェクトルート data/ に作成するとエンジン／監視が停止します。

- data/kill.flag
  - Monitoring 側の KillSwitch が条件を満たすと write されます（例: ドローダウン超過やポジション上限）。
  - ExecutionEngine はこれを見て安全に停止します。
  - `Settings.kill_flag_clear_on_start` が 1 の場合、起動時に kill.flag を自動クリアする設定があるので本番では 0 を推奨。

- PID ファイル
  - data/execution.pid に ExecutionEngine の PID が書かれます（設定で変更可能）。

---

## Directory（主要ファイルと説明）

以下は src/kabusys 配下の主なファイル / モジュールの簡易構成です。

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン）
  - config.py                  — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite に対する永続化層（テーブル初期化／CRUD）
    - system_monitor.py        — システム / データ鮮度監視
    - trade_monitor.py         — （発注・約定監視、コード参照先がある想定）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各モニタを束ねるエンジン
    - alert_manager.py         — （アラート送信管理、LINE 等を想定）
  - execution/
    - execution_engine.py      — 実行エンジン（EngineConfig 等）
    - broker_factory.py        — BrokerClient の生成（paper/live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py       — Momentum / Volatility / Value 等
    - feature_exploration.py   — IC / forward returns / summary
  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリング
    - regime_detector.py       — マクロ + ETF MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

（上記は主要ファイルのみ抜粋。実際のリポジトリに応じて詳細を参照してください）

---

## 開発上の注意 / 運用メモ

- 環境分離:
  - paper_trading モードは paper_trading_db を使い、本番データと分離するように設計されています。
- ログ:
  - setup_logging は stdout（StreamHandler）と日次ローテートファイルの両方を設定します。ログディレクトリ作成に失敗した場合はコンソールみログのみになります。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます（psutil の権限が必要）。
- OpenAI:
  - news_nlp / regime_detector は OpenAI API を利用します。API キーは OPENAI_API_KEY に設定してください。API 呼び出しは冪等性やリトライを考慮した実装になっていますが、コスト・レート制限に注意してください。
- データ鮮度:
  - SystemMonitor は DuckDB 側の prices_daily の最新日付をチェックして `data_freshness_ok` を判定します。データ投入パイプラインとの同期に注意。

---

## サポート / 追加資料

- 設定用テンプレート: .env.example（ある場合）
- コンフィグ生成スクリプト: scripts/generate_config.py（存在する場合）
- 設計ドキュメント参照: PortfolioConstruction.md / StrategyModel.md（コメントに言及あり）

---

README はここまでです。実行時や運用で不明点があれば、どの部分（起動スクリプト、環境変数、AI 呼び出し、DB スキーマ等）について詳しく知りたいか教えてください。必要に応じてコマンド実行例や .env のサンプルテンプレートを作成します。