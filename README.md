# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視ユーティリティ群です。本リポジトリは以下の主要機能群を含みます：実行エンジン（ExecutionEngine）／監視（Monitoring）／ポートフォリオ構築ロジック／ファクター計算・研究ツール／AI を用いたニュースセンチメント評価 等。

## 主な特徴
- ExecutionEngine：ブローカーとのインタラクション（本番 / ペーパー両対応）、注文管理、再同期（Reconciler）
- Monitoring：システム状態・注文・リスク監視、LINE 通知、ダッシュボード（Streamlit）
- Portfolio：候補選定、重み計算、ポジションサイジング、セクター制約
- Research：DuckDB を用いたファクター計算（Momentum / Volatility / Value）や特徴量解析（IC 等）
- AI モジュール：OpenAI を用いたニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- Paper Trading：KABUSYS_ENV=paper_trading の場合、ブローカーをモックし専用 SQLite に記録して本番 DB と完全分離
- 運用上の安全策：Kill Switch（drawdown やポジション上限で Execution を停止するフラグ）、stop フラグでの安全終了

---

## 準備・セットアップ

前提
- Python 3.9+
- SQLite は標準ライブラリで利用可能
- 以下の外部パッケージが必要（プロジェクトに requirements.txt があればそちらを使用してください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

環境変数
- .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
- 主な環境変数:
  - JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
  - KABU_API_PASSWORD — （必須）kabu API パスワード
  - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
  - KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
  - PAPER_FILL_MODE — Paper Trading のフィルモード: `instant`|`partial`|`never`|`reject`（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動消去するか（"1" で有効）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値

例 .env（最小）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
OPENAI_API_KEY=sk-...
```

データディレクトリ
- デフォルトでは `data/` 配下に DB / PID / フラグファイルが生成されます。必要であれば環境変数でパスを上書きしてください。

---

## 起動・使い方

プロジェクトルートで実行する想定です（.git や pyproject.toml からプロジェクトルートを自動検出する実装あり）。

1. 監視プロセス（Monitoring）起動
   - デフォルトは production DB パス（Settings.sqlite_path）を使用して監視データを記録します。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）。
   ```
   python -m kabusys.run_monitoring
   ```
   - 停止するにはプロセスを Ctrl+C するか、プロジェクトルートの `data/stop_requested.flag` を作成します（監視ループが検知して終了します）。

2. 実行エンジン（ExecutionEngine）起動
   - KABUSYS_ENV により振る舞いが変わります。`paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
   ```
   python -m kabusys.run_execution
   ```
   - ExecutionEngine は PID を `data/execution.pid` に書きます。停止は `data/stop_requested.flag` を作成するか、ExecutionEngine 内の Kill Switch（`data/kill.flag`）により停止されます。

3. Streamlit ダッシュボード（監視 UI）
   - 読み取り専用で monitoring.db を参照します。起動:
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - DB が存在しない／開けない場合はエラーが表示されます（MonitoringEngine を先に起動してください）。

4. Paper Trading 検証レポート
   - Paper Trading DB（デフォルト: data/paper_trading.db）に対して検証レポートを出力します。期間指定可能。
   ```
   python -m kabusys.tools.paper_verification_report
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   ```

5. AI 関連（プログラムからの呼び出し）
   - OpenAI API キー（OPENAI_API_KEY）を設定して、プログラムから次の関数を呼べます:
     - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を集約して ai_scores に書き込む
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジームを判定して書き込む
   - API 呼び出しにはリトライやクリップ等の安全策が組み込まれています。

停止フラグと Kill Switch
- data/stop_requested.flag — run_monitoring / run_execution などのループを安全に終了させるために使われます（存在を検知するとプロセスが終了します）。
- data/kill.flag — KillSwitch が検出条件（例: 大きなドローダウン）を満たした際に作成され、ExecutionEngine に停止を促します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で削除されます。

---

## 設定の自動読み込み
- Settings モジュールはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
  - 読み込み順（優先度高→低）: OS 環境変数 > .env.local > .env
  - 自動読込を無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要コマンドまとめ
- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（Settings）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py — SQLite による監視ログの永続化
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — kill.flag の作成・評価ロジック
    - alert_manager.py — LINE Push（通知）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, ... — 注文管理関連ロジック
    - run_execution.py（エントリ）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み
    - risk_adjustment.py — セクター制約・レジーム乗数
    - position_sizing.py — 株数計算、集約キャップ
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。詳細はソースを参照してください。）

---

## 運用上の注意 / ベストプラクティス
- 本番で OpenAI を使う場合は API キーとコスト管理に注意してください。news_nlp はチャンク／トリム／リトライの安全策を持ちますが、呼び出し回数は増えます。
- Paper Trading を利用することで実際のブローカーに影響を与えずに検証できます（PAPER_TRADING_SQLITE_PATH に記録）。
- kill.flag / stop_requested.flag の操作は慎重に行ってください（特に本番環境）。
- ログレベルは環境変数 LOG_LEVEL で制御できます。運用時は INFO 〜 WARNING、障害解析時は DEBUG を推奨します。
- DuckDB / SQLite のファイルパスは Settings で上書き可能です。バックアップ・永続化方針を設計してください。

---

## 開発・拡張
- 新しい監視ルールは monitoring/*.py に Monitor クラスを追加し、MonitoringEngine に組み込んでください。
- AI モジュールは API 呼び出し部分をモック（テスト用に _call_openai_api を patch）してユニットテストできます。
- Portfolio モジュールは純粋関数群で設計されているため、単体テストがしやすい構成です。

---

もし README に追加したい具体的な項目（例: CI の設定、テスト実行方法、サンプル .env.example など）があれば教えてください。必要に応じて追記します。