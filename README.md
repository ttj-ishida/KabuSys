# KabuSys

日本株向け自動売買システムのコアライブラリ群と実行用スクリプト群です。  
このリポジトリには取引エンジンの起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築・リスク制御ロジック、研究（リサーチ）用モジュール、AI を使ったニュース解析などが含まれます。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とその監視・安全停止（Kill Switch）を提供します。
- Paper trading（ペーパートレード）モードをサポートし、本番 DB と分離して検証できます。
- DuckDB を用いた価格・財務データ処理、SQLite を用いた監視ログ・トレードログ保存。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメントや市場レジーム判定の機能を備えます（APIキー必要）。
- モジュールはテストしやすい純粋関数群（ポートフォリオ構築・リスク調整など）で構成されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動（本番 / paper_trading 切替）
  - ブローカー抽象化（MockBrokerClient を含む）
  - 注文管理・リスク管理・再整合（Reconciler）
- Monitoring
  - SystemMonitor：プロセス生存・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch：条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記モニタをまとめて定期実行
- Portfolio
  - 候補選定・重み計算（等金額・スコア重み）
  - セクター制約・レジーム乗数の適用
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（Information Coefficient）や統計サマリー
- AI
  - ニュースを LLM でセンチメント評価して ai_scores に書き込み（score_news）
  - マクロニュース + ETF MA を合成して市場レジームを判定（score_regime）
- ユーティリティ
  - 環境設定ウィザード（.env 生成）
  - 設定検証 CLI（.env と config/*.yaml のチェック）
  - Paper Trading 検証レポート出力ツール

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証時に YAML 検査を行う場合）

実際のインストール方法は本リポジトリの requirements.txt があればそれを使用してください（本スニペットには含まれていません）:
```
pip install -r requirements.txt
```

不足ライブラリがあると一部機能（AI / YAML 検証 等）がスキップまたは警告されます。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install -r requirements.txt
   ```

2. 対話式ウィザードで .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants リフレッシュトークン、kabu API パスワードなどの必須項目を入力します。
   - .env は絶対に Git にコミットしないでください。

3. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```
   - PyYAML がない場合は YAML 検証がスキップされます（警告）。

4. データベース初期化
   - 初回起動時に必要なテーブルはスクリプトが自動で作成します（Monitoring は init_monitoring_db を実行します）。
   - DuckDB / SQLite のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード）

5. 環境変数の自動読み込み
   - パッケージ起点でプロジェクトルート（.git または pyproject.toml）を探し、.env → .env.local の順でロードします。
   - 自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 主要な環境変数（Settings で参照）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

詳細は `src/kabusys/config.py` を参照してください。

---

## 使い方（主なコマンド）

- 設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替
  - ペーパートレードでは MockBrokerClient を使い paper_trading.db に記録
  ```
  python -m kabusys.run_execution
  ```
  - 起動時、data/stop_requested.flag が存在する場合は起動せず終了します。
  - 起動中に data/stop_requested.flag を作成すると実行中エンジンを安全に停止します。

- Monitoring 起動（単体のシステム監視ループ）
  ```
  # ポーリング間隔を変更したい場合:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 実行時は環境にかかわらず本番 SQLite（Settings.sqlite_path）を監視用 DB として使います。
  - デフォルト間隔: 60 秒

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 周り（ライブラリ関数）
  - news_nlp.score_news、regime_detector.score_regime はプログラムから呼んで使用します（OpenAI APIキーが必要）。

---

## データ / フラグファイル

- data/kabusys.duckdb — DuckDB（価格・財務・ニュース等の分析用）
- data/monitoring.db — SQLite（監視ログ / trade_logs / positions / risk_logs / dashboard）
- data/paper_trading.db — SQLite（paper_trading 専用）
- data/execution.pid — 実行中の ExecutionEngine の PID（run_execution が書き込み）
- data/stop_requested.flag — run_monitoring / run_execution による停止フラグ（存在で停止）
- data/kill.flag — KillSwitch が書き込む緊急停止フラグ（存在で ExecutionEngine 停止）

注意: KillSwitch は条件が成立した際（ドローダウンやポジション上限等）に data/kill.flag を作成します。KILL_FLAG_CLEAR_ON_START を `1` にすると起動時に自動でクリアされますが、本番では `0` を推奨します。

---

## ディレクトリ構成（主なファイル）

プロジェクトのルートは src/kabusys 以下にあります。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (未表示スニペットのため詳細はコード参照)
  - execution/                (発注エンジン関連: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, ...)
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/                     （実行時に使用する DB・フラグ等を置く想定）

（上記はリポジトリ内の主要モジュールの抜粋です。詳細は各ファイルを参照してください。）

---

## 開発者向けメモ / 注意点

- 自動で .env をプロジェクトルートから読み込みます（.env.local は .env の上書き）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- Monitoring は監視専用で、run_monitoring は Settings.env に関係なく本番 sqlite_path を参照します（監視と実行エンジン DB は分離する設計）。
- Paper trading モード（KABUSYS_ENV=paper_trading）では paper_sqlite_path を使用し、本番 DB と完全分離されます。
- OpenAI を使う機能は API のレート制限やエラーを想定してエクスポネンシャルバックオフや部分失敗時の保護（部分的に書き込む）を実装していますが、APIキーと使用量に注意してください。
- process priority と CPU affinity は psutil を使用します。権限不足で操作できない場合は警告ログが出ますが起動は継続します。

---

## よくあるトラブルと対処

- "環境変数が未設定" のエラー:
  - config_setup で .env を作成し、必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。
  - または環境変数を直接 export してください。
- DuckDB / SQLite ファイルがない:
  - 初回起動時に監視用テーブルは自動作成されます。ただし DuckDB の prices_daily 等のテーブルは別途データ投入が必要です。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY の設定、ネットワーク、API 利用制限、モデル名（gpt-4o-mini）の可用性を確認してください。
- PID/FLAG 関連:
  - run_execution は実行中に data/execution.pid を書きます。停止させたい場合は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が書かれるのを待ちます。

---

開発にあたっては各モジュールの docstring とログ出力を参考にしてください。README に不足している点や実行時に出たログメッセージで不明点があれば、その箇所のソースコードを参照するかご質問ください。