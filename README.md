# KabuSys

日本株向けの自動売買システム（プロトタイプ）。システム監視・リスク監視・発注実行・ポートフォリオ構築・ファクター研究・ニュースNLP 等のモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 発注を行う ExecutionEngine（本番 / ペーパートレード切替）
- システム状態・注文・リスクを監視する MonitoringEngine（Kill Switch 実装）
- ポートフォリオ構築（銘柄選定、重み計算、株数決定）
- ファクター計算・特徴量探索（DuckDB を用いたオフライン解析）
- ニュースの LLM（OpenAI）によるセンチメント解析と市場レジーム判定
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）
- ログ設定・プロセス優先度設定などのユーティリティ群

設計方針として、本番口座や取引APIへ直接アクセスする処理と、解析や研究用処理は明確に分離されており、ペーパートレード用の DB を分けるなど安全性に配慮されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注処理（本番 / paper_trading 切替）
  - RiskManager / OrderManager / Reconciler 等の実装（設定による制限）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
  - TradeMonitor：注文滞留や約定異常の検出（trade_logs を参照）
  - RiskMonitor：ドローダウン・ポジション上限の監視と通知
  - KillSwitch：重大リスクで data/kill.flag を書き込み Execution を停止
- Portfolio
  - 銘柄候補選定、等重・スコア重み、セクター上限適用、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai_scores テーブル）
  - マクロニュース + ETF MA を用いた市場レジーム判定（market_regime テーブル）
- ツール
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil 使用）

---

## 必要要件（推奨）

- Python 3.10+
- SQLite（Python 組み込み）
- インストールする Python ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML を検証したい場合）
- （任意）仮想環境（venv / pyenv 等）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成 & 依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. 必要ディレクトリ作成（`data/`, `logs/`）
   ```bash
   mkdir -p data logs
   ```

4. 環境変数設定（.env の作成）
   - 対話式ウィザードで .env を作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（最低限設定が必要なもの）
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
   - そのほか（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL / LOG_DIR 等

   > 注意: .env は決してリポジトリにコミットしないでください。

5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告もFAIL扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. （必要なら）データベースの初期化は各起動スクリプトが自動で行います（init_monitoring_db によるテーブル作成/マイグレーション）。

---

## 実行方法（使い方）

- ExecutionEngine（発注エンジン）起動
  - 停止フラグや PID 関連は data/ 配下を使用します。
  - ペーパートレード時は KABUSYS_ENV=paper_trading を指定すると MockBrokerClient と専用 DB を使います。
  ```bash
  # 本番 or development 環境（環境変数で切替）
  python -m kabusys.run_execution
  ```

  実行時のポイント:
  - 起動時にプロセス優先度を "high" に設定します。
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用。
  - 起動前に data/stop_requested.flag が存在するとエンジンは起動しません。
  - 実行中に data/stop_requested.flag を作成するとループが検知して終了します。

- Monitoring（監視ループ）起動
  ```bash
  # ポーリングループを起動
  python -m kabusys.run_monitoring

  # ポーリング間隔を環境変数で上書き（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  特記事項:
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）でポーリング間隔を変更可能。1秒未満や非正整数は無視されデフォルトを使用。
  - Monitoring は KABUSYS_ENV に関係なく settings.sqlite_path（監視 DB）を参照します。
  - data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env ウィザード（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- AI 機能（プログラムから呼び出す例）
  - ニューススコアリング:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="...")  # api_key を渡すか OPENAI_API_KEY 環境変数を設定
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="...")
    ```

- 停止・Kill Switch
  - システム的に ExecutionEngine を停止させたい場合、KillSwitch が条件を満たすと data/kill.flag を書き込みます（Execution が起動時にこのフラグを検知して停止する設計）。
  - 手動で即時停止させたい場合は `data/stop_requested.flag` を作成すると run_monitoring / run_execution 等のループが検知して停止します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリアします（本番では推奨されません）。

- ログ
  - デフォルトで stdout（コンソール）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
  - LOG_DIR / LOG_LEVEL により挙動を変更できます。

---

## 主要な設定項目（例）

最低限必要な環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意設定（デフォルト値）:
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY (AI 機能使用時)

例: .env（一部）
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## ディレクトリ構成（概観）

以下は主要なファイル/ディレクトリの構成（src/kabusys 配下）と各役割の概略です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読込、Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 層（初期化 / CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文監視; 実装参照）
    - risk_monitor.py — ドローダウン、ポジション上限監視
    - kill_switch.py — kill.flag 操作ロジック
    - monitoring_engine.py — 各モニタの束ね
    - alert_manager.py — アラート送信（LINE など、実装参照）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（座組み）
    - broker_factory.py — BrokerClient の生成（実環境 / Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りの責務分離
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数決定・資金配分ロジック
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント化（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ETF）
  - tools/
    - paper_verification_report.py — Paper Trading 向け検証レポート生成
  - data/ (実行時に生成される、リポジトリ直下)
    - monitoring / paper_trading DB 等が配置されることを想定
    - stop_requested.flag, kill.flag, execution.pid などの制御ファイルを格納

（実際のリポジトリには上記以外のモジュール・ファイルや未掲の補助スクリプトが存在する可能性があります。上記は提供されたコードから抜粋した構成図です）

---

## 注意事項 / 運用上のポイント

- 本番（KABUSYS_ENV=live）では設定ミスが重大な誤発注に繋がるため、validate_config の実行と設定の慎重な確認を強く推奨します。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- AI（OpenAI）を使用する機能は API コストとレイテンシの影響を受けます。API キー漏洩対策を行ってください。
- Monitoring は production sqlite_path を参照します（監視は常に本番 DB を見る設計）。Execution は paper_trading の場合専用 DB に分離されます。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続する挙動があります（ログ設定ユーティリティの挙動）。

---

## 開発 / 貢献

- コードスタイルやテストは各自の開発ガイドラインに従ってください。
- テスト時は .env 自動ロードを無効化するために環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。
- 外部 API 呼び出し（OpenAI 等）はモック化してユニットテストを行ってください（モジュール内で API 呼び出し関数を差し替えられるよう設計されています）。

---

必要であれば、README に含めるコマンド例や .env のテンプレートをさらに詳しく作成します。どの部分を追加したいか教えてください。