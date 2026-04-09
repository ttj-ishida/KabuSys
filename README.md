# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。  
ポートフォリオ構築、ポジションサイズ算出、リスク制御、DuckDB ベースの因子計算、OpenAI を使ったニュース NLP、取引エンジン（kabuステーション想定）、監視 / アラート機能（LINE）などを備えています。

主な設計方針は「DB / ブローカー依存を分離した純粋関数や単一責務コンポーネントの組み合わせ」で、テスト容易性と事故時の安全性（リコンシリエーション／kill switch / 冪等書き込み）を重視しています。

## 主な機能一覧

- 環境変数読み込みと設定管理（auto .env ロード）
- ポートフォリオ構築
  - 候補選定 (score ranking)
  - 等金額 / スコア加重配分
  - セクター上限フィルタ
  - レジームに基づく乗数
- ポジションサイズ決定（リスクベース・重みベース）、単元株丸め、aggregate cap
- リサーチ / ファクター計算（DuckDB を利用）
  - Momentum / Volatility / Value 等のファクター
  - 将来リターン、IC や統計サマリ
- ニュース NLP（OpenAI）による銘柄別センチメント集計と ai_scores 書き込み
- 市場レジーム判定（ETF MA とマクロニュースを LLM で評価）
- ExecutionEngine（Signal Pull + WebSocket Push ドレイン）
  - OrderManager / Reconciler（再起動時の自動復旧）
  - RiskManager を介した Gate 構造と kill switch
- 監視機能
  - MonitoringDB（SQLite）へのログ永続化
  - System / Trade / Risk Monitor
  - LINE によるアラート（AlertManager）
  - Streamlit ダッシュボード（read-only）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の | 演算子、新しい型表記を使用）
- Git, pip（任意: 仮想環境推奨）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール（最低限）
   ```bash
   pip install duckdb openai requests psutil streamlit
   ```
   - 実行環境や CI では追加パッケージが必要になる場合があります。requirements.txt があればそちらを利用してください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（起動時に自動ロードされます）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (OpenAI を使う機能で必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (監視アラート)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_FILL_MODE (instant | partial | never | reject)（Paper Trading 用）
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

   例 `.env`（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

5. データディレクトリの作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

6. Monitoring DB の初期化
   簡単な Python スクリプトでテーブルを作成できます:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（主要なモジュールの例）

- 設定の参照
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- DuckDB を使ったファクター計算（例: モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- AI ニューススコア（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20))  # OpenAI キーは引数か環境変数で渡す
  ```

- Monitoring Streamlit ダッシュボード（read-only）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（本番的な使い方は依存オブジェクトの実装が必要）
  - BrokerAPIProtocol に準拠したブローカークライアント（kabu station client など）
  - OrderRepository（SQLite ベース）
  - RiskManager（リスク判定ロジック）
  - Reconciler（オプション）

  実行イメージ（擬似コード）:
  ```python
  engine = ExecutionEngine(
      broker=your_broker_impl,
      repo=your_order_repo,
      risk_manager=your_risk_manager,
      order_manager=your_order_manager,
      duckdb_conn=duckdb.connect(str(settings.duckdb_path)),
      config=EngineConfig(target_date=date.today()),
      reconciler=your_reconciler,
  )
  engine.run_session()
  ```

- 監視機能（RiskMonitor / SystemMonitor / TradeMonitor 等）は MonitoringDB（SQLite）を渡して使用します。AlertManager は LINE 用トークンと user_id を渡して初期化します。

---

## 自動 .env 読み込みの挙動（補足）

- 起動時、`kabusys.config` は実行ファイル位置（__file__ の親階層）から上位へ探索してプロジェクトルートを特定します（.git または pyproject.toml を基準）。
- 見つかったプロジェクトルートに存在する `.env` と `.env.local` を読み込みます。
  - まず `.env` を未設定キーに対して読み込み（OS 環境変数を保護）。
  - 次に `.env.local` を上書きモードで読み込み（テストやローカルオーバーライド向け）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数/設定管理、Settings クラス（自動 .env 読込を含む）

ai/
- news_nlp.py — raw_news を集約し OpenAI で銘柄別センチメントスコアを計算して ai_scores へ書込む
- regime_detector.py — ETF(1321) の MA とマクロニュースを LLM で組合せて market_regime を算出
- __init__.py — ai.score_news をエクスポート

portfolio/
- portfolio_builder.py — 候補選定、等重/スコア重み計算
- position_sizing.py — 株数算出、aggregate cap、lot_size 考慮
- risk_adjustment.py — セクターキャップ適用、レジーム乗数
- __init__.py — 主要 API をまとめて export

research/
- factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン、IC、統計サマリ、ランク関数
- __init__.py — 主要 API をまとめて export

monitoring/
- monitoring_db.py — SQLite 用のスキーマ初期化と MonitoringDB ラッパー
- risk_monitor.py — ドローダウン / ポジション上限の監視
- trade_monitor.py — 注文滞留 / 約定価格異常の検出
- system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID 管理
- kill_switch.py — kill.flag ファイルによる停止シグナルの発行
- alert_manager.py — LINE Push API 経由のアラート送信
- monitoring_engine.py — 各モニタを束ねるポーリングエンジン
- streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード（read-only）
- __init__.py — 主要 API をまとめて export

execution/
- broker_api.py — Broker API のデータモデル / Protocol / 例外
- order_manager.py — Order 상태遷移と broker 呼び出し周りの永続化ロジック
- reconciler.py — 再起動時の注文照合・ポジション差分検出
- execution_engine.py — Signal Pull + Push Drain の実行エンジン
- その他（order_repository, order_record, risk_manager 等は別ファイルとして想定）

data/
- (データファイルや DB を置く場所: data/kabusys.duckdb, data/monitoring.db など)

ドキュメント内の各モジュールは README の記述どおりの責務に従っており、ユニットテストや CI を組み込むことで安全に運用可能です。

---

## 注意点 / 運用上のヒント

- OpenAI を利用する機能（news_nlp, regime_detector）は API 失敗時にフォールバック（安全側）するよう実装されていますが、API キーの管理には注意してください。
- ExecutionEngine は kill.flag / PID ファイル / 再起動時のリコンシリエーションを備えており、複数プロセスの同時実行を防ぐ仕組みが含まれています。運用前に設定ファイル（.env）と DB の初期化を必ず行ってください。
- DuckDB のデータ鮮度（prices_daily 等）は監視機能でチェックされます。データ更新パイプラインとの連携を保ってください。
- Paper Trading（paper_trading 環境）用の設定があり、PAPER_FILL_MODE によってモックブローカーの挙動を制御できます。

---

必要であれば、具体的な起動スクリプト、Dockerfile、requirements.txt、あるいは ExecutionEngine を動かすためのサンプル実装（サンプル Broker クライアント / OrderRepository の雛形）を README に追記します。どの部分を優先して追加しましょうか？