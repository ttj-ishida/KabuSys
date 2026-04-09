# KabuSys

日本株向けの自動売買支援ライブラリ / ミニ実行基盤。  
ポートフォリオ構築、ポジションサイジング、ファクター研究、ニュース NLP による銘柄センチメント評価、実行エンジン周りの発注制御・監視機能などを含みます。

---

## プロジェクト概要

KabuSys は以下の機能群をモジュール化したコードベースです。  
設計方針として「本番ブローカー呼び出しと研究ロジックを分離」「DB（DuckDB / SQLite）を用いたデータ永続化」「LLM を使ったマクロ / ニュースのセンチメント評価」「起動時リコンシリエーションと監視アラート」を重視しています。

主な用途例:
- 日次のファクター計算・ポートフォリオ構築（DuckDB の価格・財務データを前提）
- ニュース記事を LLM で評価して銘柄ごとにスコア化（ai_scores テーブルへ保存）
- 市場レジーム判定（ETF MA + マクロニュースの LLM センチメント）
- 発注エンジン（ExecutionEngine）による信号処理・ブローカ API 連携（抽象化された BrokerAPIProtocol）
- 監視コンポーネント（監視ログ DB、リスクモニタ、アラート送信、kill switch）
- 研究用ユーティリティ（フォワードリターン・IC 計算・ファクター統計）

---

## 主な機能一覧

- 環境変数 / .env 自動読み込み（.env, .env.local、優先度あり）
- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額配分 / スコア加重配分
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（リスクベース・金額ベース）、単元株丸め・aggregate cap
- 研究（research）
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）・統計サマリー
- AI（LLM）関連
  - ニュースセンチメントスコア化（OpenAI: gpt-4o-mini を想定）
  - 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）
  - 再試行・レスポンスバリデーション・部分書込みでのフェイルセーフ処理
- 実行（execution）
  - OrderManager / Reconciler / ExecutionEngine（Signal Queue Pull + push ドレイン）
  - Broker API 抽象（OrderRequest/OrderStatus/Position 等のデータモデルと例外）
- 監視（monitoring）
  - MonitoringDB（SQLite）と CRUD ラッパー
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
  - AlertManager（LINE Push）
  - Streamlit ダッシュボード（read-only 表示対応）

---

## 要件（推奨）

- Python 3.10+
- 主な Python パッケージ（プロジェクトの requirements.txt がなければ次をインストール）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
- （オプション）SQLite は標準ライブラリで利用可能

例:
```
pip install duckdb openai requests psutil streamlit
```

---

## 環境変数一覧

settings クラス / コードで参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE push 用トークン（AlertManager）
- LINE_USER_ID — LINE push 送信先ユーザー ID（AlertManager）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading のフェイク約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするフラグ（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基に .env, .env.local を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env のパースはシンプルながらシングル/ダブルクォートや export 形式、行内コメント等に対応しています。

---

## セットアップ手順（ローカル検証用）

1. リポジトリをクローン / 配布を展開
2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存をインストール
   ```
   pip install -r requirements.txt  # もし用意されていれば
   ```
   または最小限:
   ```
   pip install duckdb openai requests psutil streamlit
   ```
4. 環境変数を設定（例: .env）
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```
5. Monitoring DB 初期化（SQLite）
   Python スクリプト例:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（代表的な例）

- Streamlit ダッシュボード起動（監視 DB を read-only で開く）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- DuckDB を渡してファクターを計算（研究用）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

- ニュース NLP（OpenAI API）で ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"{n_written} 銘柄を書き込みました")
```

- 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

- ポートフォリオ構築の一連（候補選定 → ウェイト → ポジションサイズ）
```python
from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

buy_signals = [
    {"code": "1234", "signal_rank": 1, "score": 0.9},
    {"code": "5678", "signal_rank": 2, "score": 0.5},
    # ...
]

candidates = select_candidates(buy_signals, max_positions=5)
weights = calc_equal_weights(candidates)  # or calc_score_weights
sizes = calc_position_sizes(
    weights=weights,
    candidates=candidates,
    portfolio_value=10_000_000,
    available_cash=1_000_000,
    current_positions={},
    open_prices={"1234": 1200.0, "5678": 800.0},
)
```

- ExecutionEngine（概要）
  - ExecutionEngine は BrokerAPIProtocol を実装したクライアント、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig を受け取り、1 日のセッション（シグナル処理 / push drain）を実行します。実稼働では PID ファイル管理や kill.flag を利用して安全停止を行います。直接使用する場合はコード中の docstring と型定義を参照してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / Settings
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート・等重/スコア重み
    - position_sizing.py — 発注株数決定、aggregate cap、単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — momentum / volatility / value 等の factor 計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — ニュース記事を LLM でスコアリング → ai_scores に書き込み
    - regime_detector.py — ETF MA + マクロニュース LLM でレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ・MonitoringDB ラッパー
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE Push
    - monitoring_engine.py — 複数モニタの統合ポーリング
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
    - __init__.py
  - execution/
    - broker_api.py — Broker API のデータモデル・例外・Protocol
    - order_manager.py — 発注の状態遷移とブローカー呼び出しの永続化戦略
    - reconciler.py — 起動時リコンシリエーション（注文・ポジション照合）
    - execution_engine.py — Signal 処理と push ドレインループ
    - (その他 execution 関連モジュール)
  - monitoring/ (上記)
  - research/, portfolio/ (上記)

---

## 注意点 / 設計上の留意事項

- DuckDB / SQLite のテーブルスキーマやデータ前処理は外部で用意する必要があります（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）。
- OpenAI 呼び出し部分は API 失敗時にフェイルセーフ（スコアをスキップ、または中立値にフォールバック）する設計です。API キーの管理とリクエスト制限に注意してください。
- ExecutionEngine / OrderManager 等はブローカー API を抽象化しているため、実際のブローカークライアントを BrokerAPIProtocol に準拠して実装する必要があります。
- .env の自動読み込みはプロジェクトルートの検出に基づくため、パッケージ展開後に .env を配置する場合は .git もしくは pyproject.toml の存在場所に注意してください。自動読み込みを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## 貢献

バグ修正・改善提案はプルリクエストで歓迎します。テストの追加やドキュメントの改善も助かります。

---

## ライセンス

プロジェクトのライセンスはリポジトリの LICENSE を参照してください（この README にはライセンス情報を含めていません）。