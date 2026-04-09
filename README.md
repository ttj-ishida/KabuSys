# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視のためのライブラリ兼ミニフレームワークです。  
DuckDB / SQLite を用いたデータ処理、ポートフォリオ構築ロジック、発注エンジン、監視（LINE 通知や Streamlit ダッシュボード）、およびニュースを LLM（OpenAI）でスコアリングする機能を備えています。

---

## 概要

主な設計方針・特徴：

- ファイナンス特有のロジック（ポートフォリオ構築、ポジションサイジング、セクター制約、レジーム判定など）は純粋関数として実装され、テストしやすい設計。
- DuckDB を使ったオンプレ型のリサーチ/ファクター計算（prices_daily / raw_financials / raw_news 等のテーブルを前提）。
- 発注系は BrokerAPIProtocol を想定した抽象化により実ブローカー実装に依存しない。
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP とマクロセンチメント評価機能を提供（API キー必要）。
- 監視・アラート機能（LINE push）、監視 DB（SQLite）への永続化、Streamlit ダッシュボードを備える。
- 起動時リコンシリエーション、kill.flag による外部停止シグナルなど運用を考慮した安全機構あり。

---

## 主な機能一覧

- 環境変数 / .env 自動ロード（`kabusys.config`）
- ポートフォリオ構築
  - シグナル選定（select_candidates）
  - 等配分・スコア加重配分（calc_equal_weights / calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - セクター制約適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリューファクター計算（DuckDB ベース）
  - 将来リターン計算 / IC 計算 / 統計サマリ
- AI（OpenAI）連携
  - ニュースを LLM でセンチメント評価して ai_scores に書き込む（score_news）
  - マクロニュース + ETF MA を使って市場レジームを判定し保存（score_regime）
- 発注 / 実行
  - ExecutionEngine（シグナル→発注のフロー）
  - OrderManager（状態遷移 / broker API 呼出しの扱い）
  - Reconciler（起動時の自動復旧・照合）
- 監視
  - MonitoringDB（SQLite）による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / AlertManager（LINE）
  - Streamlit ダッシュボード（監視 UI）
  - KillSwitch による外部停止

---

## セットアップ手順（開発環境向け）

※以下はリポジトリ側に requirements.txt が無い想定での例です。実際はプロジェクトのパッケージング方針に合わせてください。

1. リポジトリをチェックアウト
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール
   pip install duckdb openai requests psutil streamlit

   （プロジェクトで setuptools/poetry 等を使う場合はそれに従ってください）

4. 環境変数設定 / .env
   プロジェクトルート（.git または pyproject.toml を起点）に `.env` / `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   主要な環境変数（コード上で参照される例）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_USER_ID
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_FILL_MODE (instant|partial|never|reject)
   - PAPER_TRADING_SQLITE_PATH
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - KABUSYS_ENV (development|paper_trading|live)
   - LOG_LEVEL

   例（.env）:
   ```
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABU_API_PASSWORD=your_password
   ```

5. 監視 DB の初期化（SQLite）
   以下は簡単な Python スクリプト例でテーブルを作成します：

   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

6. DuckDB の準備
   DuckDB 側は `data/kabusys.duckdb` に必要なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets, ...）を準備してください。サンプルデータ / ETL はプロジェクト外部で管理します。

---

## 使い方

以下は代表的な利用例です。

- 設定を利用する（コード内で）
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

- ポートフォリオ構築ユーティリティ
```python
from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights, calc_position_sizes

candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_score_weights(candidates)
sizes = calc_position_sizes(weights, candidates, portfolio_value=1_000_000, available_cash=700_000, current_positions={}, open_prices=price_map)
```

- ニュース NLP スコア取得（OpenAI API キーが必要）
```python
import duckdb
from kabusys.ai import score_news
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env OPENAI_API_KEY を使う
print("wrote scores for", n_written, "codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20))
```

- 監視ダッシュボード（Streamlit）
  事前に monitoring DB を作成してデータを書き込んでおく。
  実行コマンド:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine（単発実行）
  MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組み合わせて使用します。テスト時は run_once() を呼ぶことで 1 回だけ実行できます。

- ExecutionEngine
  実際の発注エンジンは多数の依存（Broker 実装、OrderRepository、RiskManager 等）を注入して使用します。テストでは ExecutionEngine._process_signals / _drain_push_queue を直接呼ぶことで挙動を確認できます。

---

## .env 自動ロードの挙動

- 自動ロード条件:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` が未設定（または空）の場合、自動ロードを試みます。
  - プロジェクトルートは `src/kabusys/config.py` の位置から親ディレクトリを遡り、`.git` または `pyproject.toml` が見つかったディレクトリをルートと判定します。見つからない場合は自動ロードをスキップします。
- ロード順序:
  - OS 環境変数 を最優先（上書きされない）
  - `.env` を読み込み（既存の OS 環境変数は保護）
  - `.env.local` を読み込み（`.env.local` は既存 OS 環境変数を保護したまま上書きする）
- パースの挙動:
  - `export KEY=val` 形式に対応
  - シングル／ダブルクォート内のエスケープ処理や行末コメント処理など一般的な .env 構文に配慮

---

## ディレクトリ構成（主要ファイルの要約）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / .env 読み込み、Settings クラス
- portfolio/
  - portfolio_builder.py — 候補選択・重み計算（等配分・スコア加重）
  - position_sizing.py — 株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクター制約・レジーム乗数
  - __init__.py
- research/
  - factor_research.py — momentum / volatility / value の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - __init__.py
- ai/
  - news_nlp.py — raw_news を LLM に投げて ai_scores を更新
  - regime_detector.py — ETF MA + マクロ NLP を組合せてレジーム判定
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite テーブル定義 / MonitoringDB クラス
  - system_monitor.py — システム / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限チェック
  - alert_manager.py — LINE push 通知クライアント
  - kill_switch.py — kill.flag ファイル操作
  - monitoring_engine.py — 各 Monitor を束ねるランナー
  - streamlit_dashboard.py — Streamlit ベースの Web ダッシュボード
  - __init__.py
- execution/
  - broker_api.py — Broker API のデータモデル・例外・Protocol
  - order_manager.py — Order state machine の外向き API
  - reconciler.py — 起動時の注文・ポジション照合
  - execution_engine.py — Signal Queue Pull 型のエンジン
  - （その他、order_repository, order_record, risk_manager 等は本リポジトリ内に存在する想定）
- その他: data/（データファイル配置想定: duckdb, sqlite, kill.flag 等）

---

## 運用メモ / 注意点

- OpenAI を使用する機能（news_nlp / regime_detector）は API キーが必須。失敗時はフォールバック動作（多くはスコア 0.0）を行う設計ですが、API キー未設定時は関数が ValueError を投げます。
- ExecutionEngine は運用上の安全策（kill.flag、PID ファイル、リコンシリエーション、Gate チェック）を多数備えています。実運用時はこれらの挙動を十分確認してください。
- DuckDB のテーブル構成・データ整備（prices_daily 等）は本 README の外側で準備する必要があります。
- LINE 通知は channel access token と user id を設定しない場合は送信を行いません（ログのみ）。

---

## 開発・貢献

- 新機能追加やバグ修正は PR ベースでお願いします。ユニットテストを可能な限り付加してください（特に純粋関数群はテストしやすい設計です）。
- LLM 周りは外部 API 依存が強いため、テストでは API 呼出しをモックすることを推奨します（本コードはモック差し替えを想定した設計箇所あり）。

---

この README はコードベースの主要ポイントをまとめたものです。追加で「セットアップ用の requirements.txt を作る」「DuckDB 初期ロードスクリプト」「Broker のモック実装例」など具体的な補助が必要であれば指示してください。