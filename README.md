# KabuSys

日本株向けの自動売買 / リサーチ / 監視ライブラリ。ポートフォリオ構築、ポジションサイジング、リスク調整、ファクター計算、ニュースのLLMベースセンチメント評価、実行エンジン、監視ダッシュボードなどの機能を提供します。コードは純粋関数寄りの設計を意識しており、DB・API呼び出し部分は分離されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の領域をカバーします。

- ファクター計算・リサーチ（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定・等配分・スコア加重）
- ポジションサイズ計算（リスクベース・単元丸め・集計キャップ）
- リスク調整（セクター上限・市場レジーム乗数）
- ニュースの NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- Execution エンジン（シグナル処理 / WebSocket ドレイン / リコンシリエーション）
- 監視（ログ永続化、リスクモニタ、LINE 通知、Streamlit ダッシュボード）

設計上のポイント:
- DuckDB / SQLite をデータ永続化に利用（リサーチは DuckDB、監視は SQLite）
- OpenAI（gpt-4o-mini）をニュース評価・レジーム判定で使用（APIキー必須）
- .env ファイル（.env/.env.local）または環境変数から設定を読み込む自動ロード機能あり

---

## 機能一覧

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの検出）
  - 必須設定の検査（_require）
  - Settings オブジェクト（各種パス・API トークン・運用モード）

- kabusys.portfolio
  - select_candidates: BUY シグナルから候補選定
  - calc_equal_weights / calc_score_weights: 重み計算
  - calc_position_sizes: 発注株数計算（risk_based / equal / score）
  - apply_sector_cap / calc_regime_multiplier: セクター制限 / レジーム乗数

- kabusys.research
  - calc_momentum / calc_volatility / calc_value: ファクター計算（DuckDB 接続を受け取る）
  - calc_forward_returns / calc_ic / factor_summary / rank: ファクター探索・IC 計算

- kabusys.ai
  - score_news: raw_news を LLM でセンチメント評価して ai_scores に書き込む
  - score_regime: ETF MA とマクロニュースを LLM で評価して market_regime に書き込む

- kabusys.execution
  - BrokerAPIProtocol 等のクライアント契約・データモデル
  - OrderManager / Reconciler / ExecutionEngine: 発注フロー・再同期・セッション実行

- kabusys.monitoring
  - MonitoringDB: SQLite 構造化ストレージ + init_monitoring_db
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - Streamlit ベースの監視ダッシュボード（read-only で開ける）

---

## セットアップ

必要条件（代表例）
- Python 3.10+ 推奨
- 必要パッケージ（少なくとも）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
  - その他プロジェクト依存パッケージ

例: 仮想環境作成とパッケージインストール
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai requests psutil streamlit
# もし本リポジトリに pyproject.toml があれば:
# pip install -e .
```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込みます。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主なキー（例）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など

簡易 .env.example（プロジェクトに合わせて編集してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

監視 DB 初期化（SQLite）
- MonitoringDB 初期化関数を呼ぶことでテーブルを作成します（冪等）。
  例（Python）:
  ```
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  ```

---

## 使い方（代表例）

1) Python API を使ったファクター計算（DuckDB 接続を渡す）
```
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

2) ニュースセンチメントの評価（OpenAI API キー必要）
```
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

3) 市場レジーム判定（OpenAI API キー必要）
```
from kabusys.ai.regime_detector import score_regime
n = score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

4) 監視ダッシュボード（Streamlit）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- ダッシュボードは読み取り専用モードで開き、監視データを可視化します。

5) ExecutionEngine（本番的な利用）
- ExecutionEngine は Broker 実装（BrokerAPIProtocol を満たすクラス）、OrderRepository、RiskManager、OrderManager、DuckDB 接続を受け取りセッション実行を行います。実際の起動は各プロジェクト固有のランチャーから行う想定です（実行中は PID ファイルや kill.flag を使った制御あり）。

6) 監視アラート送信（LINE）
- AlertManager に LINE トークンと user_id を渡して使用。トークンが未設定の場合は送信をスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス（環境変数管理、自動 .env ロード）
- portfolio/
  - portfolio_builder.py (候補選定・重み)
  - position_sizing.py (株数決定・集計キャップ)
  - risk_adjustment.py (セクターキャップ・レジーム乗数)
- research/
  - factor_research.py (momentum/volatility/value)
  - feature_exploration.py (forward returns, IC, summary)
  - __init__.py
- ai/
  - news_nlp.py (ニュース→LLM スコアリング、ai_scores 書き込み)
  - regime_detector.py (ETF MA + マクロニュース→レジーム判定)
  - __init__.py
- monitoring/
  - monitoring_db.py (SQLite テーブル定義 / MonitoringDB)
  - risk_monitor.py (ドローダウン・ポジション数監視)
  - system_monitor.py (システム状態 / データ鮮度)
  - trade_monitor.py (滞留注文 / 約定異常)
  - alert_manager.py (LINE push)
  - kill_switch.py (kill.flag 操作)
  - monitoring_engine.py (ポーリング統合)
  - streamlit_dashboard.py (監視ダッシュボード)
  - __init__.py
- execution/
  - broker_api.py (データモデル・Protocol・例外)
  - order_manager.py (発注ステートマシン API)
  - execution_engine.py (セッション実行、push ドレイン、kill switch)
  - reconciler.py (起動時リコンシリエーション)
  - ...（OrderRepository 等は別モジュールとして想定）
- research, portfolio, ai, monitoring などの各モジュールは、DuckDB/SQLite 等の外部リソースを受け取り副作用を最小限に抑える設計です。

---

## 運用時の注意点

- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必須。API の呼び出しに失敗した際はフェイルセーフとしてスコアを 0.0 にフォールバックする実装箇所がありますが、キーが未設定の場合は呼び出し時に ValueError を投げます。
- .env 自動読み込みはプロジェクトルートを .git または pyproject.toml で検出します。配布後に CWD に依存しないよう工夫されています。
- kill.flag / PID 管理によりプロセス継続制御を行います。運用スクリプト側で適切にハンドリングしてください。
- DuckDB / SQLite のバージョン差や executemany の挙動に依存した箇所があるため、運用環境の DB バージョンに注意してください。
- 実際のブローカー連携を行う場合は BrokerAPIProtocol を実装したクライアントを用意してください（kabuステーション API 等）。

---

## 貢献・拡張ポイント（提案）

- 単元株数を銘柄毎に管理するためのマスタ拡張（position_sizing の TODO）
- ファクターの追加・正規化パイプラインの強化（zscore 正規化等）
- テスト用のモック実装（OpenAI 呼び出しの差し替えが想定済み）
- Streamlit ダッシュボードでの追加ウィジェット（リスクイベントの詳細、チャート等）

---

この README はコードベースからの推測に基づいて作成しています。実際の利用にはプロジェクトの pyproject.toml、依存定義、運用手順書を合わせて参照してください。必要であれば README の追加セクション（開発環境構築、ユニットテスト、CI 設定サンプル等）を追記します。