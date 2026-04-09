# KabuSys

日本株向け自動売買 / リサーチ基盤ライブラリの README（日本語）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引およびリサーチ用途に設計された内部ライブラリ群です。  
主な目的は以下：

- DuckDB を用いたファクタ計算・リサーチ（ファクター算出、将来リターン、IC 計算など）
- ニュースを LLM（OpenAI）でスコアリングして ai_scores に格納
- 市場レジーム判定（MA とマクロニュースの LLM センチメントを合成）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制約）
- 発注エンジン（ExecutionEngine / OrderManager / Broker API 抽象化）
- 監視基盤（MonitoringDB、各種 Monitor、LINE 通知、Streamlit ダッシュボード）
- 再起動時のリコンシリエーション用ユーティリティ

設計方針として「DB / ブローカー等の副作用は分離」「ルックアヘッドを避ける」「失敗はフェイルセーフで続行」を重視しています。

---

## 主な機能一覧

- 環境変数管理（.env / .env.local の自動読み込み、オーバーライドルール）
- Portfolio:
  - 候補選定（score 降順 + tie-break）
  - 等金額配分 / スコア加重配分
  - セクター上限適用、レジーム乗数算出
  - ポジションサイズ算出（risk-based / equal / score）、lot 単位丸め、aggregate cap
- Research:
  - Momentum / Volatility / Value ファクター算出（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）算出、統計サマリー
- AI:
  - ニュースセンチメントスコアリング（OpenAI gpt-4o-mini、JSON mode、バッチ・リトライ）
  - 市場レジーム判定（ETF 1321 MA200 乖離 + マクロニュース LLM）
- Execution:
  - Broker API の抽象化（Protocol / dataclass モデル）
  - OrderManager（状態遷移、送信・同期・キャンセル）
  - ExecutionEngine（シグナル処理・WebSocket push ドレイン・Kill Switch）
  - Reconciler（再起動時の自動復旧）
- Monitoring:
  - MonitoringDB（SQLite スキーマ/永続化）
  - System/Trade/Risk Monitor、KillSwitch、AlertManager（LINE Push）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

前提: Python 3.9+（typing の一部機能を使用）、git

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   このコードベースで用いられている主な依存ライブラリ:
   - duckdb
   - openai
   - psutil
   - requests
   - streamlit

   例:
   ```
   pip install duckdb openai psutil requests streamlit
   ```

4. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（.env.local が優先して上書き）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

   最低限設定が推奨される変数（用途に応じて追加／変更）:
   - JQUANTS_REFRESH_TOKEN (必須: J-Quants API)
   - KABU_API_PASSWORD (必須: kabu ステーション API パスワード)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - LINE_CHANNEL_ACCESS_TOKEN (監視通知用、任意)
   - LINE_USER_ID (監視通知先、任意)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB デフォルト: data/monitoring.db)
   - PAPER_FILL_MODE (paper trading の挙動: instant|partial|never|reject)
   - KABUSYS_ENV (development|paper_trading|live)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   簡単な .env の例:
   ```
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=secret
   JQUANTS_REFRESH_TOKEN=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

---

## 使い方（主要な実行例）

以下はよく使うユースケースの例です。

- Monitoring DB の初期化（SQLite 接続を渡す）
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()
  ```

- Streamlit ダッシュボードを起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ニューススコアリング（ai.news_nlp.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み件数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ExecutionEngine のセッション実行（簡易イメージ）
  実運用では Broker 実装（BrokerAPIProtocol を満たす）、OrderRepository、RiskManager、OrderManager、DuckDB 接続、Reconciler 等を組み合わせます。テスト時はモックやスタブを使って個別メソッド（_process_signals / _drain_push_queue）を呼ぶことが推奨されます。

- Research（ファクター計算）
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

注意点:
- OpenAI 呼び出しはリトライや失敗フォールバックの実装があるものの、API キーは必須です。テストでは各モジュールの _call_openai_api をモックしてください（コード内に差し替えを想定したコメントあり）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を起点に行われます。テストや CI で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- kill.flag, PID ファイルの挙動：ExecutionEngine は起動時に PID を書き込み、kill.flag を検出すると起動拒否または Kill Switch を発動します。設定は Settings 経由で変更できます。

---

## ディレクトリ構成（主要ファイルと説明）

（ルートは `src/kabusys` を想定）

- src/kabusys/
  - __init__.py — パッケージ宣言、__version__
  - config.py — 環境変数 / .env 読み込み / Settings クラス
- src/kabusys/portfolio/
  - __init__.py — ポートフォリオ API を公開
  - portfolio_builder.py — 候補選定・等配分・スコア配分
  - risk_adjustment.py — セクターキャップ、レジーム乗数
  - position_sizing.py — 実際の株数算出、aggregate cap のスケール調整
- src/kabusys/research/
  - __init__.py — 研究用 API エクスポート（zscore 正規化など）
  - factor_research.py — Momentum/Volatility/Value の計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- src/kabusys/ai/
  - __init__.py — ai のエクスポート（score_news 等）
  - news_nlp.py — raw_news を OpenAI で評価し ai_scores に書き込む
  - regime_detector.py — MA200 とマクロニュースで市場レジームを判定
- src/kabusys/monitoring/
  - __init__.py — 監視モジュールのエクスポート
  - monitoring_db.py — SQLite スキーマ作成 / MonitoringDB クラス
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度の監視
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の読み書き・評価ロジック
  - alert_manager.py — LINE プッシュ通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるループ（run / run_once）
  - streamlit_dashboard.py — Streamlit ダッシュボード（起動コマンドはソース内コメント参照）
- src/kabusys/execution/
  - broker_api.py — Broker API のデータモデル、Protocol、例外
  - order_record.py — 注文状態モデル（状態遷移ロジックはここにある想定）
  - order_repository.py — SQLite ベースの Orders 永続化（想定）
  - order_manager.py — Order 管理（作成・送信・同期・キャンセル）
  - execution_engine.py — シグナルループ、push drain、kill switch を含む実行エンジン
  - reconciler.py — 再起動時の復旧ロジック（注文 / ポジション照合）
  - risk_manager.py — 発注 Gate（設計により別ファイルとして存在）
- src/kabusys/monitoring/（上記参照）
- その他
  - data/ (デフォルトのデータベース保存先)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)

---

## 環境変数 / Settings（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push のトークン（任意）
- LINE_USER_ID — LINE Push の送信先ユーザ（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — paper trading の fill モード（instant/partial/never/reject）
- KABUSYS_ENV — environment（development/paper_trading/live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読込を無効化（1 を設定）

設定は Settings クラス経由で取得できます（例: from kabusys.config import settings; settings.duckdb_path）。

---

## テスト・開発上の注意

- OpenAI を利用する機能（news_nlp, regime_detector）は外部 API 呼び出しを伴うため、ユニットテストでは _call_openai_api をモックすることを推奨します（コード内に差し替えを想定した記述あり）。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime など）は想定されたスキーマでデータを用意してください。リサーチ関数はこれらのテーブルのみを参照します。
- ExecutionEngine 等の本番処理はブローカー実装（BrokerAPIProtocol 満たすクラス）と組み合わせて使用します。テストではモックブローカーを用いて push のシミュレーションが可能です。
- .env 読み込みはプロジェクトルートを __file__ から探索して特定するため、パッケージ配布後も一貫した動作を期待できます。

---

以上がこのリポジトリの主要な説明です。具体的な API の使い方や詳細な設計（PortfolioConstruction.md / StrategyModel.md 等）は別ドキュメントにまとめることを推奨します。必要であれば README に追加したい利用例や図、設計ドキュメントの骨子を追記しますので教えてください。