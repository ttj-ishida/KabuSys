# KabuSys

日本株向け自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、発注実行、監視、リサーチ、AI を用いたニュースセンチメント等を含む自動売買基盤の一部を実装した Python パッケージです。

---

## プロジェクト概要

- 戦略に基づく銘柄選定・配分・株数決定（portfolio/）
- 発注・約定管理・リスク管理・Reconciler を統合した ExecutionEngine（execution/）
- 実行中のシステム状態・注文状態を監視し Kill Switch を発動する監視コンポーネント（monitoring/）
- DuckDB を使ったリサーチ・ファクター計算（research/）
- OpenAI を用いたニュース NLP（ai/）
- 設定ウィザード・設定検証・運用ツール（config_setup.py, validate_config.py, tools/）
- 小さなユーティリティ（utils/）や DB 永続化層（monitoring_db など）

設計上のポイント:
- 本番用とペーパートレードを分離（KABUSYS_ENV = paper_trading 時は専用 SQLite を使用）
- .env による環境変数管理をサポート。対話式ウィザードで .env を生成可能
- OpenAI を利用するモジュールは API キー必須。失敗時はフェイルセーフ（多くはフォールバック値で継続）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（実際の発注処理フロー）
  - Broker クライアントの抽象化（本番 / モック切り替え）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の構成要素
- Monitoring
  - SystemMonitor: プロセス・CPU/メモリ/ディスク・データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出
  - KillSwitch / AlertManager 経由で外部通知・エンジン停止指示
  - monitoring DB（SQLite）への永続化（system_status / trade_logs / risk_logs / dashboard / positions）
- Portfolio construction
  - 候補抽出、等重・スコア加重配分、ポジションサイズ計算（単元丸め・aggregate cap）
  - セクター上限・レジーム乗数の適用
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores への書き込み
  - regime_detector: ETF MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - config_setup.py : 対話式 .env 生成ウィザード
  - validate_config.py : .env / config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py : ペーパートレード検証レポート生成

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | を使用しているため）
- system 標準の sqlite3 は不要なインストール要件（標準ライブラリ）

推奨パッケージ（pip インストール例）:
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）

例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

1. レポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. .env の作成
   - 対話式ウィザードを利用:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成（下の「環境変数」節を参照）
5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告も厳格に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

（.env に設定する代表的なキー）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルト値あり）:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: paper_trading 時のモック約定モード ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか (0/1)
- PID_FILE_PATH, KILL_FLAG_PATH: ファイルパスの上書き

監視ループ用:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

サンプル（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主なコマンド）

- 設定ウィザード（.env を対話式で作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 実行エンジンの起動（Execution）
  - 通常起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading を設定すると MockBroker が使われ、data/paper_trading.db に記録されます。例:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

  実行時の挙動:
  - 起動時にプロセス優先度を high に設定し、SQLite / DuckDB に接続します。
  - data/stop_requested.flag が存在すると起動を中止します。
  - 実行中に stop flag を作成すればエンジン停止をトリガーします（監視コンポーネントから kill.flag を書き込むことあり）。

- 監視ループの起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（SQLite）に書き込み、必要に応じて Kill Switch を作動させます。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連
  - news_nlp / regime_detector は OpenAI API キーを必要とします（OPENAI_API_KEY または api_key 引数）。
  - 実際にスコアを保存する操作は DuckDB 接続が必要です（ai.score_news, ai.regime_detector.score_regime）。

---

## 停止・キルフロー

- stop_requested.flag
  - run_monitoring / run_execution のトップレベルループはプロジェクト data/stop_requested.flag を検査し、存在すればループを終了します（運用側の手動停止用）。
- kill.flag
  - KillSwitch は条件（ドローダウン・ポジション上限など）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に kill.flag の有無をチェックし、clear オプションが設定されていれば自動クリアする場合があります（KILL_FLAG_CLEAR_ON_START）。

---

## ディレクトリ構成

（主要なファイル / モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings（.env 自動ロード含む）
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                  — ニュース NLP（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI）
  - portfolio/
    - portfolio_builder.py         — 候補選定・配分（等重/スコア）
    - position_sizing.py           — 株数決定・集計キャップ処理
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py           — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC・統計
  - monitoring/
    - monitoring_db.py             — SQLite の初期化 & 永続化 API
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文滞留・価格異常監視
    - risk_monitor.py              — ドローダウン・ポジション監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - monitoring_engine.py         — 各 Monitor の統合ポーリング
    - alert_manager.py             — (未掲示) 通知管理（LINE 等）
  - execution/
    - execution_engine.py          — ExecutionEngine 本体（run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - data/                          — 実行時作成されるデータ類（DB、pid, flags 等）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV は "live" に設定すると本番モードです。慎重に設定してください（validate_config は live 設定時に追加警告を出します）。
- .env は絶対にリポジトリにコミットしないでください（機密情報含む）。
- OpenAI を使う機能はレート制限・エラーに備えてリトライ実装あり。ただし API キーが漏洩しないよう運用を慎重に。
- ペーパートレードは production DB と分離されるため、安全にローカルで検証できます。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はリサーチ・AI モジュールの入力になります。これらの整備がリサーチ品質を左右します。
- monitoring_db.init_monitoring_db は冪等的にスキーマを作成・マイグレーションを行います。

---

必要に応じて README を補足します。特に運用手順（デプロイ・サービス化、systemd ユニット例、監視通知設定など）や依存パッケージのバージョン表を追加したい場合は教えてください。