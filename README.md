# KabuSys

日本株自動売買システムのパッケージ（README）。この README はコードベースの主要機能、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

注意: .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ・監視を行うモジュール群です。主な役割は以下です。

- ExecutionEngine: 発注ロジック（本番 / ペーパートレード対応）
- Monitoring: システム・注文・リスクを定期監視し、Kill Switch による自動停止を実行
- Research: DuckDB 上の価格・財務データからファクター計算と探索を提供
- AI モジュール: ニュース NLP による銘柄センチメント評価と市場レジーム判定（OpenAI を使用）
- Portfolio: 銘柄選定・配分・ポジションサイズ決定ロジック（純粋関数）

設計方針の例:
- 本番とペーパートレードは DB を分離（paper_trading モード時は data/paper_trading.db を使用）
- ルックアヘッドバイアスへ配慮（datetime.today() を参照しない等）
- フェイルセーフ: API 失敗時は影響を最小化して継続

---

## 主な機能一覧

- 実行エンジン起動: src/kabusys/run_execution.py
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading: MockBrokerClient を使用し専用 SQLite に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応
- 監視サービス起動: src/kabusys/run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL による間隔調整（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）に永続化
- 監視 DB ユーティリティ: monitoring_db (永続化レイヤ)
- Kill Switch: risk 判定で data/kill.flag を書き込み ExecutionEngine に停止信号
- Paper Trading レポート生成: src/kabusys/tools/paper_verification_report.py
- 環境設定ウィザード: src/kabusys/config_setup.py（.env の対話式生成）
- 設定検証 CLI: src/kabusys/validate_config.py（.env や config/*.yaml の事前チェック）
- Research モジュール: factor_research, feature_exploration（DuckDB を用いたファクター計算）
- AI モジュール: news_nlp（OpenAI で記事をスコアリング）, regime_detector（MA とマクロセンチメント合成）
- ユーティリティ: process_priority（プロセス優先度・CPU affinity 設定）など

---

## 必要要件（概略）

推奨 Python バージョン: 3.10+（型注釈や現代的ライブラリを使用）

依存ライブラリ（主要）:
- duckdb
- psutil
- openai
- SQLite（標準ライブラリに含む）
- PyYAML（config/*.yaml の内容検証を行う場合に必要）

※ requirements.txt は本リポジトリに含まれていないため、必要に応じて pip install を行ってください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 環境変数 / .env の主な項目

重要な環境変数（必須に近い順）:

- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
  - paper_trading: MockBroker を使い data/paper_trading.db に記録
  - live: 本番モード（実際に発注）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY: OpenAI 呼び出しで使用（news_nlp / regime_detector）
- LOG_LEVEL: INFO 等（デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0 推奨。本番では 0）

推奨: リポジトリルートに .env を置く（config_setup.py で作成可能）。

例（最低限）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
```

---

## セットアップ手順（開発 / ローカル）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（上述の環境変数を設定）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）
6. データディレクトリの確認（data/）
   - SQLite / DuckDB の親ディレクトリが存在しない場合は自動生成されることがありますが、権限やパスに注意してください。

---

## 使い方（起動・停止）

基本的にモジュールは CLI で起動します。

- ExecutionEngine（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存（paper_trading では専用 DB を使用）
  - 起動時、プロセス優先度が "high" に設定されます
  - 停止は data/stop_requested.flag を作成するか kill.flag により停止指示を受けます

- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔: 環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に sqlite_path（本番の monitoring DB）を使用します（環境にかかわらず）
  - 停止は data/stop_requested.flag を作成

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 失敗時は非ゼロ終了コードを返します

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、未指定時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（プログラムから呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key を明示的に渡すか OPENAI_API_KEY を設定

停止フラグ / 制御ファイル:
- data/stop_requested.flag: run_execution / run_monitoring によるループ停止の検出に使用
- data/execution.pid: 実行エンジンの PID ファイル（SystemMonitor はこれを監視）
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine はこのフラグで停止を受ける（本番保護）

---

## 重要な挙動・注意事項

- paper_trading モードは本番環境と DB を完全分離します（PAPER_TRADING_SQLITE_PATH を使用）。
- Monitoring は常に本番の sqlite_path（SQLITE_PATH）を参照します。テスト時は注意してください。
- OpenAI 呼び出しについて:
  - API の 429 / ネットワーク断 / 5xx はリトライを実装（指数バックオフ）
  - API キー未設定時は例外を投げるか 0.0 フォールバックする実装箇所あり（モジュールにより異なる）
- kill.flag および stop_requested.flag の自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）
- プロセス優先度と CPU affinity 設定はプラットフォーム依存で失敗することがあります（権限不足や未対応 OS の場合は警告が出てスキップされます）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数のロード / Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリング
  - regime_detector.py — マーケットレジーム判定
- monitoring/
  - monitoring_db.py — 監視ログの永続化（SQLite）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — （アラート送信のラッパー、実装箇所あり）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py 等（発注関連）
- portfolio/
  - portfolio_builder.py — 候補選定 / 等重・スコア重み
  - position_sizing.py — 株数計算（ロット丸め・制約）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity

ルート関連:
- data/ — 実行時 DB / フラグファイル配置（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/kill.flag, data/stop_requested.flag）
- config/ — YAML 設定ファイル群（system_config.yaml 等、generate_script で生成する想定）

---

## よくある運用ワークフロー（例）

1. 開発マシンで .env を作成:
   - python -m kabusys.config_setup
2. 設定検証:
   - python -m kabusys.validate_config
3. DuckDB / SQLite にデータを投入（外部 ETL スクリプト想定）
4. ペーパートレードで動作検証:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - python -m kabusys.run_monitoring
   - 試験期間の結果を確認: python -m kabusys.tools.paper_verification_report --from ... --to ...
5. 本番移行:
   - .env の KABUSYS_ENV=live をセットし、設定を慎重に確認
   - KILL_FLAG_CLEAR_ON_START は 0 を推奨

---

## 開発・貢献のヒント

- テスト用に環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い .env 自動ロードを無効化できます。
- OpenAI 呼び出し部は外部依存が強いため、ユニットテストでは _call_openai_api をモックしてください（各モジュールが想定している名前でパッチ可能）。
- DuckDB を使った処理は SQL を直接書いている箇所が多いため、テーブルスキーマ変更時は SQL クエリの整合性を確認してください。
- monitoring_db.init_monitoring_db は冪等化されており、既存 DB への最低限のマイグレーション（カラム追加等）を行います。

---

README はコードベースの概要を示すためのものです。各モジュールの詳細な使い方や API はソースコード内の docstring（およびドキュメントファイル）を参照してください。必要であればモジュール別の詳細 README を追加作成できます。