# KabuSys — 日本株自動売買システム

このリポジトリは、日本株の自動売買システム「KabuSys」のコアライブラリ群を含みます。  
README はプロジェクトの概要・機能・セットアップ・実行方法・主要ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下のコンポーネントを備えた自動売買フレームワークです。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントを用いた発注・約定管理
- リスク管理（RiskManager, Reconciler, OrderManager 等）
- 監視（Monitoring） — プロセス稼働監視、注文滞留・約定異常・ドローダウン監視
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針の一部：
- 本番・ペーパートレードを明確に分離（KABUSYS_ENV により挙動が変わる）
- DuckDB を利用したリサーチ用分析、SQLite を利用した監視ログ永続化
- OpenAI（gpt-4o-mini）を利用する AI 部分は API キーを環境変数で管理し、失敗に対してフェイルセーフ化

---

## 主な機能一覧

- 実行（run_execution.py）
  - ExecutionEngine を起動して注文実行セッションを開始
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視（run_monitoring.py / monitoring パッケージ）
  - CPU / メモリ / ディスク / 実行プロセスの生存確認
  - 注文滞留検出、約定価格の異常検出
  - ドローダウン／ポジション上限を監視して kill.flag を生成可能
  - AlertManager 経由で通知（LINE 等の設定を利用）
- 環境設定支援
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額・スコア重み配分、リスク調整、ポジションサイジング
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）等
- AI（kabusys.ai）
  - news_nlp: raw_news を LLM で解析して銘柄別スコアを ai_scores テーブルへ書込
  - regime_detector: ETF + マクロニュースを組合せて市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## 必須 / 推奨依存関係

- Python 3.10+
  - 型ヒント（X | Y 表記など）を利用しているため Python 3.10 以上を推奨
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — config/*.yaml の検証に使用
- 標準ライブラリ: sqlite3, logging など

インストール例（venv を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

プロジェクトに requirements.txt があればそれを利用してください（本リポジトリでは付属していない可能性があります）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルト値あり）:
- KABUSYS_ENV: execution 環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI を使用する機能で参照

その他:
- PAPER_FILL_MODE: paper_trading 時の約定振る舞い（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring の上書き）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 自動クリア）
- PID_FILE_PATH / KILL_FLAG_PATH 等（Settings クラス参照）

.env は git 管理しないこと。対話式ウィザードで生成可能（下記参照）。

---

## セットアップ手順（簡易）

1. Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, psutil, openai, pyyaml 等）
3. プロジェクトルートで .env を準備
   - 対話式で生成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example（ある場合）をコピーして編集
4. データディレクトリを作成
   ```
   mkdir -p data
   ```
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

注意:
- KILL_FLAG_CLEAR_ON_START が 1 の場合、本番での自動クリアは危険です（デフォルト 0 推奨）。
- monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を参照します（run_monitoring の仕様）。

---

## 使い方（主要コマンド）

- 実行エンジン（Execution）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用して data/paper_trading.db に全記録が残ります。
  - 起動時は data/stop_requested.flag が存在すると起動せず終了します。
  - ExecutionEngine は実行中に data/execution.pid を作成します。

- 監視（Monitoring）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数で上書き可能:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視ループも data/stop_requested.flag を検知すると停止します。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（OpenAI API が必要）
  - news_nlp / regime_detector は OPENAI_API_KEY を参照または引数で渡して呼び出す関数（kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime）を用います。
  - API 呼び出しはレート制限・タイムアウトに対してリトライ処理を実装していますが、APIキー・料金管理は利用者責任です。

---

## 停止・Kill Switch（運用上のポイント）

- KillSwitch は監視コンポーネント（RiskMonitor 等）から判定して data/kill.flag を書き込みます。ExecutionEngine はこのフラグを監視して停止できます。
- 手動で停止したい場合はファイルを作成:
  ```
  echo "reason" > data/kill.flag
  ```
- 実行停止要求用フラグ: data/stop_requested.flag を作成すると run_* スクリプトが検知してシャットダウンします。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動削除します（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス（環境変数 / .env 自動読み込みロジック）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity ユーティリティ
  - execution/ (実行関連)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py ...
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 / 永続化層
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の作成/判定
    - monitoring_engine.py — 各 monitor を束ねるループ
    - alert_manager.py — 通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコア計算（OpenAI 呼び出し）
    - regime_detector.py — ETF MA + マクロニュースからレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに多くのモジュールが含まれます。）

---

## 運用上の注意 / ベストプラクティス

- .env は絶対にリポジトリにコミットしないでください（トークンやパスワードが含まれます）。
- 本番（KABUSYS_ENV=live）の場合は LINE 通知設定や kill flag の設定を必ず確認してください。
- Monitoring は常に本番用の SQLITE_PATH を参照する（run_monitoring の仕様）。テスト用に監視 DB を分離したい場合は別途対応を検討してください。
- OpenAI API を利用する機能は外部 API 呼び出しを伴うため、API キー管理とコストに注意してください。
- psutil によるプロセス優先度設定は権限依存で失敗することがあるためログを確認してください。

---

README の内容はソースコードの docstring / コメントに基づく簡易まとめです。詳細実装や追加の設定ファイル（config/*.yaml 等）はリポジトリ内の該当ファイルを参照してください。必要であれば README を拡張して具体的な config/*.yaml のサンプルや実行例（systemd ユニット、Docker、CI 設定など）を追記できます。