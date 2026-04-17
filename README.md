# KabuSys

日本株向け自動売買システムのコードベース（README）  
この README はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコア機能群を提供する Python パッケージです。  
主な機能は以下のとおりです。

- 注文実行エンジン（ExecutionEngine） — 実際の発注またはペーパートレードの制御
- 監視（Monitoring） — システム状態／注文状態／リスクの継続的監視、アラート・Kill Switch
- ポートフォリオ構築（Portfolio） — 候補選定、重みづけ、ポジションサイズ算出、セクター制限
- リサーチ（Research） — ファクター計算、将来リターン、IC 解析など
- AI ヘルパー（AI） — ニュースの NLP スコアリング（OpenAI 利用）、市場レジーム判定
- ツール群 — Paper Trading の検証レポート生成など
- 環境設定ウィザード / 設定検証 CLI

設計方針の一部：
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアス防止（日時参照は引数ベース）
- フェイルセーフ：API 失敗時にスキップやフォールバックする実装
- 外部依存は限定（duckdb, psutil, openai, PyYAML（任意）など）

---

## 機能一覧（抜粋）

- run_execution.py:
  - ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）検知で安全停止
- run_monitoring.py:
  - SystemMonitor のポーリングループ起動（デフォルト 60 秒）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔変更可
  - 監視ログは sqlite（monitoring.db）へ永続化（monitoring は環境にかかわらず本番 sqlite_path を使用）
- config_setup.py:
  - .env を対話式に作成 / 更新するウィザード
- validate_config.py:
  - .env と config/*.yaml の事前検証（--strict オプションで警告を許容しない）
- tools/paper_verification_report.py:
  - Paper Trading 用 DB を解析して検証レポートを生成
- ai/news_nlp.py / ai/regime_detector.py:
  - OpenAI を使ったニュースセンチメント評価・市場レジーム判定（API キー必要）
- monitoring/*:
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine 等
- portfolio/*:
  - 候補選定、重み付け、ポジションサイズ算出、セクター上限処理 等
- utils/process_priority.py:
  - プロセス優先度・CPU affinity 設定ユーティリティ（Windows / POSIX を吸収）

---

## 前提・依存関係

- Python 3.10 以上（union 型 annotation、| などを利用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意（設定検証で YAML を検証する場合）
  - PyYAML

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# （requirements.txt がある場合）pip install -r requirements.txt
```

---

## 環境変数 / .env の取り扱い

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）から `.env` を自動ロードします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 主要な環境変数（必須・重要）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
  - PAPER_FILL_MODE（paper_trading のフィルモード: instant|partial|never|reject、デフォルト "instant"）
  - KILL_FLAG_CLEAR_ON_START（本番に注意。1 にすると起動時に kill.flag を自動クリア）
- 注意:
  - .env は絶対にリポジトリへコミットしないでください。

---

## セットアップ手順（推奨）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai pyyaml
   # 実稼働の際は requirements.txt を用意している場合はそれを使う
   ```

4. .env を作成（対話式推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須の値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. DB の初期化:
   - monitoring は起動時に必要テーブルを自動作成します（init_monitoring_db）。
   - DuckDB 用の分析 DB は別途データ投入が必要です（prices_daily / raw_financials など）。

---

## 使い方（主要な実行コマンド）

- 実行エンジン（ExecutionEngine）を起動:
  - 簡単起動（メインプロセス）:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作モードは KABUSYS_ENV で制御:
    - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - live: 実口座へ発注（環境確認とテストを十分に行ってください）。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - エンジンは data/execution.pid に PID を書きます。停止は stop flag の作成で行います（KillSwitch 経由）。

- 監視ループを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルト 60 秒ごとに SystemMonitor.check_once() を実行します。
  - ポーリング間隔を上書きする: 環境変数 `MONITOR_POLL_INTERVAL`（秒）
  - 監視は monitoring DB（settings.sqlite_path）へログを保存します。Monitoring は環境にかかわらず本番 sqlite_path を使用します（意図的）。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコアリング / レジーム判定）:
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY を設定）
  - 関数はプログラム的に呼び出します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）

---

## 停止・Kill Switch（安全停止）

- KillSwitch:
  - kill.flag（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は RiskMonitor の結果（ドローダウン・ポジション上限）を評価して自動で kill.flag を書くことがあります。
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して安全に停止します。
- 注意:
  - 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START の設定に注意（自動クリアは危険）。

---

## 主要ファイル・ディレクトリ構成

以下はソースディレクトリ（src/kabusys）を抜粋した構成と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定管理（.env 自動読み込み・Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（kill.flag 制御）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信管理（未掲載部分あり）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では必須環境変数の設定および LINE 通知設定等の確認を必ず行ってください。
- KILL_FLAG_CLEAR_ON_START を 1 にしていると起動時に既存の kill.flag を消すため誤って再起動される恐れがあります（本番では 0 推奨）。
- Paper Trading は本番 DB と分離されますが、設定ミスで上書きしないよう .env を慎重に管理してください。
- OpenAI 等外部 API を用いる機能は API キーやコスト、レート制限を考慮してください。リトライ／バックオフは実装されていますが運用監視が必要です。

---

## 追加情報 / トラブルシュート

- .env の読み込みに問題がある場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自動ロードを無効化できます。テスト等で有用です。
- DB ファイルの場所は Settings クラス経由で取得できます（デフォルト: data/*.db）。
- 監視ログやリスクログのマイグレーション処理は起動時に自動適用（列追加など）されることがあります。

---

必要に応じて README を拡張します。実際の開発・運用ワークフロー（CI、デプロイ手順、監視アラートの送信先、Broker の設定方法など）を追加したい場合は教えてください。