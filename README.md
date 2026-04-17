# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリには、ポートフォリオ構築、ポジションサイズ計算、ファクター計算、AI を利用したニュースセンチメント評価、監視/アラート、実行エンジン起動スクリプトなどが含まれます。

---

## 主な特徴（機能一覧）

- ポートフォリオ構築
  - 候補選定 (score / equal)、等金額配分、スコア加重配分
  - セクター集中制限、レジーム乗数（bull/neutral/bear）
  - 株数決定（risk-based / equal / score）、単元株丸め、aggregate cap でスケール調整
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（raw_news → ai_scores）
  - 市場レジーム判定（ETF MA200 とマクロニュースセンチメントの合成）
  - 再試行・バックオフ・レスポンス検証など堅牢な実装
- 実行（Execution）
  - ExecutionEngine 起動スクリプト、Broker クライアントファクトリ（paper_trading 対応）
  - Reconciler による起動時の自動復旧（注文状態・ポジション差分の照合）
  - OrderManager / OrderRepository による発注状態管理
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB：SQLite に対する監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch によるフラグファイルでの強制停止、LINE 通知による AlertManager
  - Streamlit ダッシュボード（read-only で監視 DB を可視化）
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - .env 自動読み込み（プロジェクトルート検出）＋ Settings クラスによる環境変数管理
- ツール
  - Paper Trading の検証レポート生成スクリプト（CSV/標準出力）

---

## 必要条件（推奨）

- Python 3.10+
- SQLite（Python 標準ライブラリに含む）
- DuckDB
- 外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（監視ダッシュボードを使う場合）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

※ 実際のプロジェクトでは requirements.txt を作成して管理してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成と依存パッケージのインストール（上記参照）

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（CWD に依存せず .git または pyproject.toml を基準に検出）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（`.env`）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-xxxxx
   PAPER_FILL_MODE=instant
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   LOG_LEVEL=INFO
   ```

4. 必要なディレクトリを作成
   ```bash
   mkdir -p data
   ```

5. SQLite / DuckDB 用の初期テーブル生成
   - 監視用 DB（monitoring.db）は起動スクリプトが init_monitoring_db() を呼び出して自動で作成・マイグレーションします。

---

## 使い方 — 実行例

### 監視ループを起動する（run_monitoring）
- 監視（SystemMonitor）をポーリングして SQLite にログを書きます。
- デフォルトのポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

起動:
```bash
python -m kabusys.run_monitoring
# または環境変数で間隔を変える
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

停止:
- プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します（スクリプト側で検出して終了）。

### 実行エンジンを起動する（run_execution）
- 実際の注文実行エンジン（ExecutionEngine）を起動します。
- `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト `data/paper_trading.db`）に完全分離して記録します。

起動:
```bash
# 本番想定
KABUSYS_ENV=live python -m kabusys.run_execution

# Paper trading
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

停止:
- `data/stop_requested.flag` を作成すると、実行エンジンが停止します（Kill/Stop のためのフラグファイル）。

### Streamlit ダッシュボード（監視データ可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開きます。DB が存在しない場合はエラーメッセージが出ます。

### Paper Trading 検証レポート生成
- paper_trading の SQLite DB を集計して検証レポートを標準出力に出します。

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を手動指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

### AI 処理（ニューススコア / レジーム判定）
- ライブラリ関数として利用可能です（スクリプト化はされていませんが、REPL やラッパースクリプトで呼べます）。

例（対話的に実行）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
# ニューススコア（OPENAI_API_KEY 環境変数が必要）
score_news(conn, target_date=date(2026,4,10))
# レジーム判定
score_regime(conn, target_date=date(2026,4,10))
```

---

## 主要設定（Settings クラス / 環境変数）

- KABUSYS_ENV: 動作モード（development / paper_trading / live） — デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で必須）
- PAPER_FILL_MODE: paper_trading のマッチングモード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB パス（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト data/monitoring.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト 60）
- PID / kill flag パス等も Settings で取得されます（PID ファイル: data/execution.pid、kill flag: data/kill.flag など）

Settings は自動的に `.env` / `.env.local` をロードしますが、OS 環境変数が優先されます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（主要ファイル）

（以下は src/kabusys/ 以下の主要ファイル/モジュールを抜粋した構成です）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数・Settings
    - utils/
      - __init__.py
      - process_priority.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - (Execution 関連モジュール群: order_manager, reconciler, execution_engine, broker_factory, etc.)
    - data/ (実行時に作成されることが想定)
- run scripts:
  - src/kabusys/run_monitoring.py
  - src/kabusys/run_execution.py

（上記は開発中の抜粋です。実際のリポジトリにはさらに多くのモジュールが含まれます。）

---

## 運用上の注意 / 実装に関する重要事項

- run_monitoring は Monitoring 用 DB（Settings.sqlite_path）を環境にかかわらず本番パスで使用します（監視は常に本番 DB を監視する想定）。
- run_execution は KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離します。
- PID / stop flag / kill flag による外部制御が採用されています。`data/stop_requested.flag` の存在でプロセスをやさしく停止できます。`data/kill.flag` は ExecutionEngine を強制停止させるために KillSwitch が作成します。
- AI 呼び出し（OpenAI）は API のエラーやレート制限を想定したリトライ実装が入っていますが、API キーの管理やコスト管理は運用面で注意してください。
- .env のパース実装はシェル風の記法（export、引用、インラインコメントなど）にかなり忠実に対応していますが、極端なケースは意図しないパースになる場合があります。`.env.example` を参照して作成してください（リポジトリに存在する場合）。

---

## 開発 / テスト時のヒント

- Settings をテストで差し替えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB と sqlite の接続は各モジュールが受け取る設計になっているため、ユニットテストではインメモリ DB（sqlite :memory: / duckdb.connect()）を使って検証できます。
- OpenAI 呼び出し部分は `_call_openai_api` を個別にモックすることでテスト可能（news_nlp.py / regime_detector.py に注記あり）。

---

## ライセンス / 貢献（任意）

- 本リポジトリのライセンスや貢献ルールはプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

この README はコードベースの主要な機能と典型的な使い方をまとめたものです。より詳細な設計や仕様はソース内の docstring、モジュール内コメント、関連ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）が参照可能であればそちらも参照してください。必要であれば README に追加すべき内容（例: 具体的な環境変数一覧、サンプル .env.example、起動時のログレベル設定方法など）を教えてください。