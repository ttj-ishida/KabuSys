# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（モジュール群）。  
このリポジトリには、実行エンジン・監視・ポートフォリオ構築・ファクター計算・AI ベースのニュース分析などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python ベースのシステムです。

- 注文実行エンジン（ExecutionEngine）: 実際の発注またはペーパートレードの切り替えで注文を送る
- 監視コンポーネント: システム状態・注文状態・リスク（ドローダウン、ポジション数）を定期チェックしアラート/Kill Switch を発動
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算等の純関数群
- リサーチ: DuckDB を用いたファクター計算・特徴探索・IC 計算
- AI モジュール: OpenAI を用いたニュース NLP（センチメント）や市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等

設計方針の一例:
- DuckDB / SQLite をデータ層に利用（分析用と監視用を分離）
- 本番環境とペーパートレードは DB を分ける（安全性）
- 自動化された設定ウィザードと事前検証機能を備える
- OpenAI 呼び出しはフェイルセーフ（失敗時にスキップ／フォールバック）を考慮

---

## 主な機能一覧

- Execution
  - run_execution.py: ExecutionEngine を起動（本番 / paper_trading を切替）
  - ブローカークライアント分離（BrokerClientFactory）による実運用 / モックの切替
  - リスク管理（RiskManager）、注文管理（OrderManager）等を組み合わせた実行フロー

- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor の統合ポーリング
  - KillSwitch によるフラグファイルでのエンジン停止制御
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard の永続化

- Portfolio construction
  - 候補選定（score / rank）
  - 重み計算（等分配、スコア加重）
  - セクター上限の適用、レジームに応じた投下資金乗数
  - 株数決定（lot 単位丸め、risk-based allocation、aggregate cap）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）算出、ファクター統計

- AI
  - news_nlp: OpenAI を用いたニュース毎のセンチメント集約と ai_scores への書き込み
  - regime_detector: ETF MA200 とマクロニュースから市場レジーム判定

- ツール
  - config_setup.py: .env を対話式で作成／更新するウィザード
  - validate_config.py: 起動前に .env / config/*.yaml の検証
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

- ユーティリティ
  - logging_setup: stdout + 日次ローテートログの統一設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（推奨）

- Python 3.10 以上（Union 型表記や新しい構文を利用）
- 推奨パッケージ（最低限）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を有効にする場合）
- SQLite（Python 標準で利用可能）
- （任意）仮想環境の利用を推奨（venv / virtualenv / poetry 等）

例: 簡易インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（デフォルトあり）
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等、デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- .env を用いる場合は config_setup.py で作成できます。
- validate_config.py で起動前検証を行ってください（--strict オプションあり）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - 画面の指示に従って必要な値を入力してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須）。
   - 本番環境では KABUSYS_ENV=live、Kill Switch の設定などに注意してください。

5. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL としたい場合は --strict を付与
   python -m kabusys.validate_config --strict
   ```

6. 初回起動前に data/ および logs/ ディレクトリが必要に応じて作成されます（ロギングが自動で作成しますが、権限に注意）。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動
  ```bash
  # 本番モード
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - paper_trading では MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
  - 起動時に data/stop_requested.flag があると起動を中断します。
  - エンジンは内部で execution.pid ファイルを扱います。

- 監視ループ起動
  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず）。
  - 停止は data/stop_requested.flag を作成することでループを抜けます。
  - run_monitoring は SystemMonitor を使って system_status を記録します。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```bash
  # 全期間
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（プログラム内呼び出し例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを CLI で呼ぶための専用スクリプトは含まれていません。API キーは OPENAI_API_KEY を設定するか引数で渡す必要があります。

---

## 停止 / Kill Switch の運用

- ExecutionEngine 停止シグナル:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止をトリガーします（実際の停止は ExecutionEngine 側で kill.flag の存在を参照して処理を中断する仕組みを想定）。
  - 管理者が強制停止する場合、data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します（スクリプト内で参照される stop flag）。

- 注意:
  - 本番運用で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します（誤動作で自動クリアされるリスクを減らすため）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール概観（src/kabusys 以下）です。

```
src/kabusys/
├─ __init__.py
├─ config.py                      # Settings クラス、自動 .env ロードロジック
├─ config_setup.py                # .env 対話式ウィザード
├─ validate_config.py             # 設定検証 CLI
├─ run_execution.py               # ExecutionEngine 起動スクリプト
├─ run_monitoring.py              # SystemMonitor ポーリング起動スクリプト

├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py            # ログ設定ユーティリティ
│  └─ process_priority.py         # プロセス優先度 / CPU affinity

├─ monitoring/
│  ├─ monitoring_db.py            # SQLite persistence layer
│  ├─ system_monitor.py
│  ├─ trade_monitor.py            # (存在: 参照されるが今回一覧には省略)
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  ├─ monitoring_engine.py
│  └─ alert_manager.py            # (存在: 参照されるが今回一覧には省略)

├─ execution/
│  ├─ execution_engine.py         # エンジン本体（参照あり）
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ reconciler.py
│  ├─ broker_factory.py
│  └─ risk_manager.py

├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py

├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py

├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py

├─ monitoring/                     # 上で列挙済み
└─ tools/
   ├─ __init__.py
   └─ paper_verification_report.py
```

（注）一部ファイルや補助モジュールはここに含めていませんが、主要な機能は上記でカバーしています。

---

## 開発・運用上の注意点

- データベース分離:
  - ペーパートレード時は paper_trading 用 SQLite を使用（本番 DB と分離）。
  - Monitoring は本番 sqlite_path を使用する設計（監視は本番 DB を参照）。

- OpenAI 利用:
  - OPENAI_API_KEY は必須（AI 機能を使う場合）。API コールはコストが発生するため注意。
  - API 呼び出しはレート制限・ネットワーク障害に対するリトライ実装あり（フェイルセーフでスコアをスキップ / 0.0 にフォールバックする箇所があります）。

- ログ:
  - setup_logging() により stdout と logs/<app_name>.log（日次ローテート）が出力されます。
  - ログディレクトリ作成に失敗した場合はコンソール出力のみ継続します。

- システムパラメータ:
  - MONITOR_POLL_INTERVAL（run_monitoring）や KILL_FLAG_CLEAR_ON_START などは環境変数で調整可能です。

- 互換性:
  - Python 3.10 以上を推奨します（型注釈などに依存）。

---

## 付録：よく使うコマンドまとめ

- 仮想環境作成 & パッケージインストール
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML
  ```

- .env 作成（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループ起動
  ```bash
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README に含める追加情報（例: API ドキュメント、ER 図、コンフィグ YAML のサンプル、CI/CD 手順、デプロイ手順など）を追記します。どの情報が欲しいか教えてください。