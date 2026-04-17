# KabuSys

日本株向けの自動売買システム（モジュール群）。  
このリポジトリには、実際の発注エンジン起動スクリプト、監視機構、ポートフォリオ構築・ポジション決定ロジック、ファクター計算・リサーチツール、AI（ニュースNLP / レジーム判定）連携などが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買基盤です。

- シグナル → ポートフォリオ構築 → ポジションサイズ計算 → 発注（ExecutionEngine）
- 発注ログ・監視（Monitoring）: システム健全性・注文滞留・約定異常・ドローダウン監視
- Paper trading（ペーパートレード）モードで本番DBと分離して検証可能
- DuckDB を用いたファクター計算・リサーチ
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（AIスコア）および市場レジーム判定
- ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証、検証レポート生成等）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を定期実行し、アラート処理を実行
- Portfolio
  - 候補選定、等分配・スコア加重、セクターキャップ、レジーム乗数、株数決定（単元丸め）、コストバッファを考慮したスケーリング等
- Research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）・統計サマリ
- AI
  - ニュース記事を集約して OpenAI に送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ保存（news_nlp）
  - ETF の MA とマクロニュースを組合せて日次の市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定
  - .env 対話ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell / CMD)
   ```

3. 依存パッケージをインストール  
   （requirements.txt がある場合は `pip install -r requirements.txt`。無い場合は主な依存を手動インストール）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - openai: AI 機能（news_nlp, regime_detector）を使う場合に必要
   - PyYAML: config/*.yaml の構文検証を行う場合に必要

4. 初期設定 (.env) の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   主要な環境変数（ウィザードで設定／または .env に手動記載）:
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意（デフォルトがあるもの）:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - LOG_LEVEL — デフォルト: INFO
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時に使用）
     - OPENAI_API_KEY — AI 機能を使うなら必須
     - PAPER_FILL_MODE — ペーパートレードの成行執行モード（instant|partial|never|reject）（デフォルト: instant）

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告もエラー扱いで終了コード 1 を返します。

---

## 使い方

基本的な実行・運用例を示します。各スクリプトはパッケージとして実行できます。

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH: data/paper_trading.db）に記録され、本番 DB とは分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - Monitoring は環境に関わらず Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（監視 DB は本番 DB を参照する設計）。
  - 監視ループは data/stop_requested.flag の存在を検知すると終了します。

- 停止・Kill Switch
  - Monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に対する停止シグナル（Kill Switch）を発動できます。KillSwitch は冪等に動作します（既に存在する場合は書き換えない）。
  - 実行を手動で停止したい場合は data/stop_requested.flag を作成してください（どちらのスクリプトもこのフラグを監視します）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db
  - 期間フィルタや --db オプションで別 DB を指定できます。

- AI 機能（ライブラリ利用例）
  - ニューススコアリング（プログラム的に）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    n = score_news(conn, target_date=date(2026,4,10), api_key='sk-...')
    ```
  - レジーム判定
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect('data/kabusys.duckdb')
    score_regime(conn, target_date=date(2026,4,10), api_key='sk-...')
    ```
  - 注意: OPENAI_API_KEY が未設定の場合、これらは例外を投げます（または API エラー時にはフォールバックで継続する実装箇所があります）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO / DEBUG / ...
- OPENAI_API_KEY: OpenAI を利用する場合必須
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant | partial | never | reject）

（.env へ記載して管理する想定。config_setup.py で生成可能）

サンプル（.env の一部）
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
```

---

## 運用メモ / 注意点

- Monitoring は常に Settings.sqlite_path（監視 DB）を使用します。paper_trading 環境でも監視 DB は本番のパスを参照する仕様（意図的）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB に記録します（本番 DB とは完全分離）。
- Kill Switch（data/kill.flag）を自動で作成するのは Monitoring 側のロジックです。Production（live）環境での設定（LINE通知等）は validate_config が警告を出しますので慎重に設定してください。
- OpenAI API を利用する機能はネットワーク・コスト・レスポンスの不確実性を伴います。API キーとコスト管理に注意してください。
- psutil を使ってプロセス優先度を変更しますが、権限や OS によって制限されるため失敗する場合があります（警告ログのみ）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB のスキーマ + CRUD
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信ロジック: LINE 等）※ファイル末尾が抜けている可能性あり
  - ai/
    - news_nlp.py — ニュース集約 → OpenAI でセンチメント → ai_scores 書込
    - regime_detector.py — MA とマクロニュースでレジーム判定
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/ (参照されるが本リストに含まれる外部モジュール)
    - execution_engine.py, order_repository.py, order_manager.py, broker_factory.py, etc.（発注ロジック）
  - data/ (運用時に DB・フラグ等を配置)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag

---

## テスト & 開発

- 設定関連の小規模ユーティリティ（config_setup, validate_config）は CI/ローカル実行での確認が容易です。
- DuckDB / sqlite を使ったロジックはローカル DB を作成してユニットテストを用意してください（モジュールは外部 API に直接アクセスしないよう設計されていますが、AI モジュールは OpenAI を呼びます。テスト時はモック推奨）。
- news_nlp / regime_detector の OpenAI 呼び出し部分は、テストで差し替え可能（内部の _call_openai_api を patch する設計）。

---

README は以上です。必要であれば以下も提供します：
- .env.example のサンプル
- systemd / supervisor 用の起動ユニット例（production 用）
- よくあるトラブルシューティング（DB マイグレーション、OpenAI エラー対処など）

どれを追加しますか？