# KabuSys

日本株向けの自動売買 / リサーチ / 監視フレームワークです。  
DuckDB を用いた時系列データ処理、LINE 通知、OpenAI を用いたニュース NLP、発注エンジン、監視・リコンシリエーション等のコンポーネントを含みます。

## 概要
KabuSys は、戦略の研究（ファクター計算・特徴量探索）、ポートフォリオ構築（候補選定・重み決定・ポジションサイズ計算）、ニュースの NLP によるセンチメント評価、市場レジーム判定、実際の発注エンジンおよび監視基盤（ログ保存 / アラート送信 / kill switch）を備えたモジュール群です。  
設計方針として、DB 参照は明示的に受け取った接続のみを使用し、本番 API 呼び出しはクライアント層に集約、LLM 呼び出しは失敗耐性（リトライ・フォールバック）を持たせる、など安全性を重視しています。

## 主な機能
- 環境変数 / .env 自動ロード（プロジェクトルート検出）
- 研究用ファクター算出
  - Momentum（1M/3M/6M リターン、MA200乖離）
  - Volatility（20日 ATR、流動性指標）
  - Value（PER / ROE）
  - 将来リターン / IC / 統計サマリー
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等金額・スコア加重配分
  - セクター集中制限適用
  - レジーム乗数
  - ポジションサイズ計算（リスクベース / equal / score、lot 数丸め、投下資金スケーリング）
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースを集約、LLM によりセンチメントを算出し ai_scores に書き込み
  - バッチ処理・リトライ・レスポンス検証・スコアクリップ（±1.0）
- レジーム判定（ETF + マクロニュースの合成、LLM利用）
- 発注エンジン（ExecutionEngine）
  - シグナル処理（Gate チェック群）→ 発注（OrderManager）→ push ドレイン
  - リコンシリエーション（再起動時の注文照合）
  - Kill switch / PID 管理 / 安全な永続化手順
- 監視（Monitoring）
  - SQLite に監視ログ保存（system_status / trade_logs / positions / risk_logs / dashboard）
  - RiskMonitor / SystemMonitor / TradeMonitor
  - AlertManager（LINE push）
  - Streamlit ベースの監視ダッシュボード（read-only 接続）

## セットアップ

前提
- Python 3.10+（型注釈に union 演算子等を使用）
- DuckDB、requests、openai、psutil、streamlit など

例: 仮想環境を作って依存をインストールする
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai requests psutil streamlit
# 開発モードでパッケージをインストールする場合
pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら送信はスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper trading の fill 動作 ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等の監視系設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の自動ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を起点）を探索して .env / .env.local を自動ロードします。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 使い方（代表的な実行例）

DuckDB 接続を用いたファクター計算（研究）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

ニュースのスコアリング（OpenAI 必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026,3,20), api_key="sk-...")
print(f"written {n_written} scores")
```

レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026,3,20), api_key="sk-...")
```

監視 DB の初期化（SQLite 接続）
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

Streamlit ダッシュボード起動
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

ExecutionEngine（概念的な例）
- 実運用では BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続等を組み合わせて ExecutionEngine を生成し、run_session() を呼びます。テスト環境ではモックを渡して run_once 相当の処理を確認します。

簡易（擬似コード）
```python
from datetime import date, time
from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
# broker, repo, risk_manager, order_manager, duckdb_conn, reconciler を準備
config = EngineConfig(target_date=date.today(), signal_send_start=time(8,50), signal_send_end=time(9,10))
engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, config, reconciler=reconciler)
engine.run_session()
```

注意: 実際の運用では各コンポーネント（ブローカークライアント等）を実装し、環境変数や DB を正しく準備した上で実行してください。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数と .env 自動読み込み、Settings オブジェクト
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — ETF とマクロニュースを合成して市場レジーム判定
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - portfolio/
    - portfolio_builder.py — 候補選定・配分重み
    - position_sizing.py — 株数決定・投下資金スケーリング・lot 丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化（init / MonitoringDB）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - alert_manager.py — LINE 通知
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 各モニタのポーリング統合
    - streamlit_dashboard.py — Read-only ダッシュボード（streamlit）
  - execution/
    - broker_api.py — Broker API 型定義 / 例外 / データモデル / Protocol
    - order_repository.py —（Orders DB 操作）※実装は別ファイル（省略されている場合あり）
    - order_record.py — 注文状態遷移ロジック（純粋オブジェクト）
    - order_manager.py — OrderState Machine の外向け API
    - reconciler.py — 再起動時の自動復旧・ポジション照合
    - execution_engine.py — Signal を処理し発注するエンジン
  - portfolio、ai、research、monitoring の各 __init__.py によるエクスポート

（上記は本リポジトリの主要モジュールを抜粋したものです。各ファイルに詳細ドキュメントコメントを含みます。）

## 注意事項 / 運用上のヒント
- OpenAI 呼び出しには API キーが必要です。api_key 引数を渡すか OPENAI_API_KEY を設定してください。API 失敗時は多くの処理がフォールバック（スコア = 0.0 等）する設計です。
- .env ロードはプロジェクトルート (.git または pyproject.toml) を想定します。配布パッケージとしてインストールした後の挙動に注意してください。自動ロードを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine はプロセス PID 書き込みや kill.flag に依存した運用モデルです。複数プロセスでの同時稼働等を行う場合は設定を確認してください。
- DuckDB / SQLite のスキーマやテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）は本リポジトリ内の SQL または初期投入スクリプトで準備してください（本 README では個別スキーマ定義は省略）。

---

より詳細な API ドキュメントや運用手順（DB スキーマ、broker 実装ガイド、CI/デプロイ手順など）は別ドキュメントにまとめることを推奨します。必要であれば README に追記する部分（例: requirements.txt の具体的内容、テストの実行方法、SQLite/DuckDB の初期ロード例など）を指定してください。