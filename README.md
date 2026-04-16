# KabuSys

KabuSys は日本株向けの自動売買基盤（プロトタイプ）です。市場データの集計・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。本リポジトリは主に以下を目的としています：戦略研究（Research）・ポートフォリオ構築（Portfolio）・本番/ペーパートレード用の実行基盤（Execution）・稼働監視（Monitoring）・検証用ツール。

概要、機能一覧、セットアップ手順、使い方、主要ディレクトリ構成を下にまとめます。

---

## プロジェクト概要（短く）

- 名前: KabuSys
- 目的: 日本株自動売買のための統合ライブラリと運用用バイナリ群
- 主な技術スタック: Python、SQLite（監視用 DB / ペーパートレード DB）、DuckDB（市場データ解析）、OpenAI API（ニュース NLP / レジーム判定）、psutil、streamlit（ダッシュボード）
- 設計方針: モジュール化、DB を介した永続化、フェイルセーフ（API失敗時のフォールバック）、ルックアヘッドバイアス防止（日時参照設計）

---

## 主な機能一覧

- Execution（発注・エンジン）
  - ExecutionEngine（run_execution 起動スクリプト）
  - Broker クライアント抽象化／MockBroker（paper_trading 用）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期）
  - リスク管理（RiskManager）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / PID / データ鮮度
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限チェック
  - KillSwitch：条件により ExecutionEngine を停止するフラグ生成
  - AlertManager：LINE push による通知
  - monitoring DB（SQLite）の初期化・読み書きユーティリティ
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

- Research（調査・ファクター計算）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリ

- Portfolio（銘柄選定・配分・ポジションサイジング）
  - portfolio_builder: 候補選定・等金額／スコア重み
  - risk_adjustment: セクター上限・レジーム乗数
  - position_sizing: 株数決定、lot 単位、投下資金スケーリング

- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news(): raw_news を OpenAI に送って銘柄ごとにセンチメントを ai_scores に書込
  - regime_detector.score_regime(): ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を更新

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
  - その他ユーティリティ（process_priority など）

---

## セットアップ手順

前提:
- Python 3.10+（typing の | None 等を使用）
- シェル環境（Linux / macOS / Windows いずれも一部機能は差分あり）
- 必要な外部サービス: OpenAI（AI機能を使う場合）、LINE（アラートを使う場合）

例: 仮想環境作成とパッケージインストール（最低限）
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai requests streamlit
# 必要に応じて他パッケージを追加
```

プロジェクトの実行方法（一時的に import パスを通す）
```bash
# ソースツリーのルートにいる前提（src ディレクトリがある）
export PYTHONPATH=src:$PYTHONPATH
```
または package をインストールして使う：
```bash
pip install -e .
```
（該当 setup.py / pyproject.toml があればこちらを推奨）

データフォルダの準備:
```bash
mkdir -p data
# デフォルトの SQLite / DuckDB ファイルは data/monitoring.db, data/kabusys.duckdb
```

環境変数の設定:
- .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な環境変数（要設定項目あり）:
  - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI（AI機能を使う場合）
  - KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE — paper_trading のフィルモード: instant|partial|never|reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH, KILL_FLAG_PATH など（必要に応じて）

注意:
- AI 機能を利用する場合は OPENAI_API_KEY を必ず設定してください。未設定だと score_news / score_regime はエラーになります。
- process priority の設定（psutil.nice 等）は権限により失敗することがあり、その場合ログでスキップされます。

---

## 使い方（コマンド例）

1. 監視ループの起動（Monitoring）
```
# パッケージとして実行する場合
python -m kabusys.run_monitoring

# もしくはソース直実行
PYTHONPATH=src python src/kabusys/run_monitoring.py
```
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）。
- 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV にかかわらず）。監視 DB の初期化は自動（init_monitoring_db）。

2. 実行エンジンの起動（Execution）
```
python -m kabusys.run_execution
# または
PYTHONPATH=src python src/kabusys/run_execution.py
```
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書きます。
- 停止方法: data/stop_requested.flag を作成するとループが検知して安全に停止します。
- 起動時、kill.flag が既にある場合は起動しない挙動あり（設定に依存）。

3. Streamlit ダッシュボード（監視の可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- DB を読み取り専用で開きます（streamlit の引数 --db でパス指定）。

4. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```
- --db を省略すると環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルトを参照。

5. AI モジュールの呼び出し（例: Python スクリプト内）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime  # 直接 import 可能

conn = duckdb.connect("data/kabusys.duckdb")
# news scoring
n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
# regime scoring
r = score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
```
- score_news / score_regime は OpenAI API 呼び出しを内部で行います。APIキーは引数または環境変数 OPENAI_API_KEY で指定可能。
- API 呼び出しはリトライやエラーハンドリングを実装しているため、API 側の一時的な障害にはある程度耐性があります。

---

## 実行時のフラグファイル・PID の扱い

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視・実行ループ中に参照する停止フラグ。存在すれば安全終了します。
- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送ります（主に監視 → 実行への保護措置）。
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル。SystemMonitor はこのファイルを見てプロセス生存確認を行います。

---

## 主要ディレクトリ構成（ソースの概略）

以下は src/kabusys 配下の主要ファイル／モジュールの抜粋です。

```
src/kabusys/
├─ __init__.py                 # バージョン・パッケージ公開
├─ config.py                   # .env 自動読み込み、Settings クラス
├─ run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
├─ run_execution.py            # ExecutionEngine 起動スクリプト
├─ tools/
│   └─ paper_verification_report.py
├─ utils/
│   └─ process_priority.py     # プロセス優先度 / CPU affinity
├─ monitoring/
│   ├─ monitoring_db.py
│   ├─ system_monitor.py
│   ├─ trade_monitor.py
│   ├─ risk_monitor.py
│   ├─ kill_switch.py
│   ├─ alert_manager.py
│   ├─ monitoring_engine.py
│   └─ streamlit_dashboard.py
├─ execution/
│   ├─ execution_engine.py
│   ├─ order_manager.py
│   ├─ order_repository.py
│   ├─ reconciler.py
│   └─ broker_factory.py
├─ portfolio/
│   ├─ portfolio_builder.py
│   ├─ position_sizing.py
│   └─ risk_adjustment.py
├─ research/
│   ├─ factor_research.py
│   └─ feature_exploration.py
├─ ai/
│   ├─ news_nlp.py
│   └─ regime_detector.py
└─ data/ ... (実行時に使うファイル群)
```

- DuckDB は研究・ファクター計算用（市場データ: prices_daily, raw_financials, raw_news 等）。
- SQLite は監視ログ（monitoring.db）やペーパートレード（paper_trading.db）用。

---

## 設定の詳細（主な Settings）

Settings クラス（kabusys.config.Settings）で管理される代表的な設定：

- KABUSYS_ENV: development | paper_trading | live（必須ではないが無効値は例外）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading のモック注文約定モード（instant/partial/never/reject）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: データファイルのパス
- LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値等

.env に書くと便利です（自動読み込みされます）。OS 環境変数が優先され、.env.local は .env を上書きできます。

---

## 運用上の注意 / トラブルシューティング

- process priority（高優先度）を設定する処理は権限を必要とすることがあります。権限不足時はログに警告が出て処理をスキップします。
- OpenAI / LINE API の鍵は秘匿に管理してください。ログに平文を出さない運用を推奨します。
- Monitoring は常に "本番の monitoring.sqlite_path" を参照します。テスト時は paper_trading 用 DB を別途使うことで本番 DB と分離してください。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials 等）に依存するため、DuckDB のデータ準備が必要です。
- DB マイグレーション: monitoring_db.init_monitoring_db は起動時に簡単なスキーマ変更（カラム追加）を行います。大規模なマイグレーションが必要な場合は別途対応してください。

---

## 最後に（開発者向けメモ）

- コード設計は「副作用を最小にした純粋関数」「DB を介した永続化」「外部 API 呼び出しのフェイルセーフ」を意識して組まれています。テスト時は .env 自動読み込みを無効化すると好都合です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- 各コンポーネントは比較的独立しているため、モックやユニットテストで個別に検証しやすくなっています（例: news_nlp._call_openai_api を patch してテスト可能）。

---

もし README に追記したいサンプル .env 内容、systemd 用のサービス定義例、あるいは運用手順（デプロイ / ログローテーション / バックアップ）などがあれば、要望に合わせて追記します。