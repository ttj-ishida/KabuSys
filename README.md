# KabuSys

日本株向け自動売買システムのサブセット実装。ポートフォリオ構築、ポジションサイズ計算、監視、ペーパートレード検証、ニュース NLP / レジーム判定（OpenAI）などのユーティリティ群を含みます。

以下はリポジトリ内のコードに基づく README です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- 株式戦略のためのファクター計算・特徴量解析（research）
- ポートフォリオ選定・ウェイト計算・ポジションサイズ決定（portfolio）
- ExecutionEngine（発注ロジック）およびペーパートレード用の分離された DB 運用
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュースを用いた AI（OpenAI）ベースのセンチメントスコアリングと市場レジーム判定（ai）
- .env の対話式セットアップ（config_setup）と設定検証 CLI（validate_config）
- ペーパートレードの検証レポート生成ツール

設計上のポイント:
- 本番とペーパー（paper_trading）で SQLite DB を分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を分析用に利用（prices_daily / raw_financials 参照）
- OpenAI API の利用箇所は API キー必須。失敗時のフェイルセーフ実装あり
- 自動で .env をロード（プロジェクトルートの .env / .env.local）。無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 主な機能一覧

- 環境セットアップウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config （--strict で警告も失敗扱い）
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
- Monitoring ポーリング: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.news_nlp.score_news(...) — ニュースを集約して OpenAI で銘柄ごとセンチメントを算出し ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime(...) — MA200 とマクロニュースでレジーム判定
- ポートフォリオ構築ユーティリティ:
  - 候補選定、等分配・スコア加重配分、セクターキャップ適用、ポジションサイズ計算
- 監視:
  - system_status / trade_logs / positions / risk_logs / dashboard を持つ monitoring DB（SQLite）への永続化と監視ロジック
  - Kill Switch（data/kill.flag）により ExecutionEngine を安全停止

---

## 前提・依存関係

- Python 3.10+
- 推奨 Python パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を有効にする場合）
- （任意）psutil の一部機能は OS 権限が必要になることがあります（プロセス優先度・CPU affinity 設定等）。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します。

2. 仮想環境を作成して依存をインストールします（上記参照）。

3. 環境変数を作成（対話式推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   - J-Quants / kabuステーション / OpenAI 等のキーをここで設定できます。
   - 生成される `.env` は決して Git にコミットしないでください。

4. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も含めて厳密に確認する場合:
   python -m kabusys.validate_config --strict
   ```

5. DB の初期化:
   - monitoring 用の SQLite は run_monitoring / run_execution 内で自動的にテーブルを作成します（init_monitoring_db）。
   - DuckDB（分析用）はデータ投入が必要です（prices_daily 等のテーブル）。

---

## 主要環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）

- DB/ファイルパス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)

- Paper Trading:
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)

- Monitoring:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

- OpenAI:
  - OPENAI_API_KEY: ai.news_nlp / ai.regime_detector で使用

- その他:
  - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START

.env 自動読み込み:
- プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env の抜粋）:
```env
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

---

## 使い方（主要なコマンド）

- 環境設定ウィザード（.env を生成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV で切り替え:
  ```bash
  # 例: ペーパートレードで起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - ペーパートレードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に注文やログを保存します。
  - 実行時に data/stop_requested.flag が存在すると起動を行わず終了します。Engine は実行中に stop flag を検知すると停止処理を行います。

- Monitoring 起動
  ```bash
  # デフォルト 60 秒間隔。環境変数で上書き可
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - run_monitoring は monitoring 用の SQLite（settings.sqlite_path）および DuckDB に接続し SystemMonitor を動かします。
  - 停止は data/stop_requested.flag を作成することで促せます（存在を検知してループを抜けます）。

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB は data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または明示的に DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコア付け / レジーム判定（プログラムから呼び出す）
  - OpenAI API キーが必要:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Kill Switch
  - risk_monitor / monitoring_engine 経由で条件を満たすと KabuSys は `data/kill.flag` を書き込みます。ExecutionEngine は起動時および実行中に kill.flag を検出すると安全停止のトリガーになります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に自動で kill.flag をクリアします（本番では 0 を推奨）。

---

## 停止方法（ランタイム）

- 実行/監視プロセスを手動で停止する:
  - data/stop_requested.flag を作成すると run_execution.run や run_monitoring のループが検出して終了します。
  - kill_switch が動作すると data/kill.flag が作成され、ExecutionEngine に停止シグナルとして扱われます。

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live で注意喚起を行います。
- OpenAI API はコストとレイテンシに注意してください。news_nlp と regime_detector はリトライ・バックオフを実装していますが、API キーの漏洩やコスト超過には注意が必要です。
- monitoring DB のスキーマ変更は init_monitoring_db で一部マイグレーション（列追加）を行います。必要に応じてバックアップを取りながら運用してください。
- process priority / cpu affinity の設定は psutil の権限に依存します。権限不足時は警告が出てスキップされます。

---

## ディレクトリ構成（主要ファイル）

下記はリポジトリ内の主要なモジュールとサブパッケージの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込み
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・集約 cap
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — Momentum / Volatility / Value 等の計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — マクロ + MA200 によるレジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py             — monitoring DB 層（SQLite）
    - system_monitor.py            — CPU / メモリ / データ鮮度 チェック
    - trade_monitor.py             — 滞留注文 / 約定異常 チェック
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書込ユーティリティ
    - monitoring_engine.py         — 各 Monitor を束ねてポーリング
    - alert_manager.py             — （アラート送信管理）※ファイルは存在します
  - execution/
    - order_repository.py          — order DB 操作（OrderRepository）
    - order_manager.py             — OrderManager（ブローカと連携）
    - execution_engine.py          — ExecutionEngine（main ロジック）
    - broker_factory.py            — Broker クライアント生成
    - reconciler.py                — 注文整合処理
    - risk_manager.py              — リスク管理ロジック
    - order_record.py              — OrderState 等の定義
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

---

## 追加情報 / トラブルシューティング

- DuckDB / SQLite の接続エラーやファイルパスエラーは、validate_config である程度検出できます。
- OpenAI API 呼び出しが失敗する場合、news_nlp/regime_detector はフェイルセーフで 0.0 にフォールバックするかスキップする実装です。ログ（INFO/WARNING/ERROR）を参照してください。
- psutil 関連（プロセス優先度や CPU affinity）の操作は環境によって失敗することがあります。ログに警告が出た場合は無視して動作可能です。

---

必要であれば README をさらに展開して、運用手順（systemd ユニット / Docker / コンテナ化手順）、より詳細な .env.example、スキーマ定義やサンプルクエリ、ユニットテストの実行方法などを追記できます。どの情報を追加しますか？