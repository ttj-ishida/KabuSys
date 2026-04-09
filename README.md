# KabuSys

日本株向け自動売買・リサーチ基盤ライブラリ / プロジェクト README。  
このドキュメントはリポジトリ内の主要モジュール（ポートフォリオ構築、リサーチ、AI ベースのニュースセンチメント、実行エンジン、監視システム等）を使い始めるための概要と手順を示します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・運用基盤を構成するモジュール群です。DuckDB / SQLite を用いたデータ操作、戦略用ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、ブローカーとの照合（Reconciler）、監視（MonitoringEngine / AlertManager / KillSwitch）、および OpenAI を用いたニュース NLP（センチメントスコアリング）などを含みます。

設計方針のポイント：
- 各モジュールは可能な限り副作用を避けた純粋関数で実装（テスト容易性向上）。
- 重要操作（DB 書き込み・ブローカー呼び出し等）は冪等性・クラッシュ安全性を意識。
- ルックアヘッドバイアスを防ぐため、日付参照で現在時刻を直接参照しない設計。
- OpenAI 呼び出し等はフェイルセーフ（失敗時にデフォールト値を利用して継続）を優先。

---

## 主な機能一覧

- 環境変数 / .env の自動読み込み（プロジェクトルート判定: .git / pyproject.toml）
- ポートフォリオ構築
  - 候補銘柄選定、等価/スコア加重重み、ポジションサイズ計算（単元株丸め・リスク制限）
  - セクター集中上限の適用、レジームに応じた乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI（OpenAI）
  - ニュース記事から銘柄別センチメントを計算して ai_scores テーブルへ保存（score_news）
  - マクロニュース + ETF MA200 を組合せて市場レジームを判定し market_regime へ保存（score_regime）
- 実行（Execution）
  - Signal Queue に基づく発注フロー（OrderManager, ExecutionEngine）
  - ブローカー照合 / 再同期（Reconciler）
  - 注文状態・キャンセル・フェイルセーフ処理
- 監視
  - システム状態、注文滞留、約定異常、ドローダウン監視（MonitoringEngine）
  - LINE を使った通知（AlertManager）
  - kill.flag による外部停止シグナル（KillSwitch）
  - Streamlit ベースの監視ダッシュボード

---

## 要件

- Python 3.10 以上（型ヒントに union 型演算子 `|` を使用）
- 必要なパッケージ（主なもの）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード用)
- SQLite（標準ライブラリ）
- Git（プロジェクトルート検出に推奨）

（好みで仮想環境の利用を推奨）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   例: pip を使う
   ```
   pip install duckdb openai requests psutil streamlit
   ```

   （実際のプロジェクトでは requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（代表例）：
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須な箇所あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所あり）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使うとき）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
   - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper trading 動作 ("instant"|"partial"|"never"|"reject")
   - PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: environment ("development"|"paper_trading"|"live")
   - LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

   簡易的な `.env` 例:
   ```
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ユースケース）

以下は代表的な実行方法の例です。各モジュールはライブラリとしても使えるように設計されています。

1. 監視 DB の初期化（SQLite）
   Python スクリプトまたは REPL で:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

2. Streamlit ダッシュボードを起動
   ─ 開発中の簡単な監視 UI
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   引数 `--db` で SQLite ファイルを指定。デフォルトは `data/monitoring.db`。

3. ニュース NLP（OpenAI）でスコアを生成して DB に書き込む
   - DuckDB への接続を作り、score_news を呼ぶ例:
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # target_date: スコアを算出する「日付」を指定
   n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
   print("書込銘柄数:", n_written)
   ```

4. 市場レジーム判定（OpenAI を使う）
   ```python
   from kabusys.ai.regime_detector import score_regime
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
   ```

5. リサーチ関数の利用例（ファクター計算）
   ```python
   from datetime import date
   import duckdb
   from kabusys.research import calc_momentum, calc_volatility, calc_value

   conn = duckdb.connect("data/kabusys.duckdb")
   d = date(2026, 3, 20)
   mom = calc_momentum(conn, d)
   vol = calc_volatility(conn, d)
   val = calc_value(conn, d)
   ```

6. 実行エンジン（ExecutionEngine）起動（概念）
   - ExecutionEngine は複数のコンポーネント（BrokerAPI 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続等）を組み合わせて起動します。実際の起動はアプリ固有のランナーや CLI を通す想定です。本 README ではエンジン設計と主なフローを説明していますが、起動スクリプトはプロジェクト固有に実装してください。
   - kill.flag の検査・PID ファイル管理、WebSocket の push ドレイン、Gate1/2/3 によるリスクチェックなどの挙動に注意してください。

---

## ディレクトリ構成（src/kabusys の主要ファイルと説明）

- src/kabusys/
  - __init__.py
    - パッケージ定義（バージョン、エクスポート）
  - config.py
    - 環境変数 / .env 読み込み、自動ロードロジック、Settings クラス（各種設定プロパティ）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算（等金額 / スコア重み）
    - position_sizing.py: 株数決定・単元丸め・投下金額スケール
    - risk_adjustment.py: セクターキャップ、レジーム乗数
    - __init__.py: 主要関数のエクスポート
  - research/
    - factor_research.py: Momentum / Volatility / Value ファクター計算
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー
    - __init__.py: 研究用 API のエクスポート
  - ai/
    - news_nlp.py: ニュース記事の OpenAI によるセンチメントスコアリング（ai_scores へ書込）
    - regime_detector.py: ETF MA200 + マクロニュース（LLM）で市場レジーム判定（market_regime へ書込）
    - __init__.py
  - monitoring/
    - monitoring_db.py: SQLite スキーマ作成・DB 操作用ラッパー（MonitoringDB）
    - system_monitor.py: システム / データ鮮度監視
    - trade_monitor.py: 注文滞留・約定異常監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の読み書き
    - alert_manager.py: LINE 通知（push）ラッパー
    - monitoring_engine.py: 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py: Streamlit ダッシュボード
    - __init__.py
  - execution/
    - broker_api.py: ブローカー API のデータモデル、Protocol、例外定義
    - order_manager.py: 発注フロー（OrderManager）
    - order_repository.py: （このコードベース内に無いが実装が存在する想定）DB 操作
    - reconciler.py: 起動時リコンシリエーション（注文・ポジション同期）
    - execution_engine.py: Signal Queue ベースの発注エンジン（セッション走行）
    - risk_manager.py: （別ファイル想定）Gate チェックロジック
    - order_record.py: （別ファイル想定）OrderRecord と状態遷移ロジック
  - その他（data pipeline / stats 等のユーティリティモジュールが存在する想定）

---

## テスト・開発メモ

- DB スキーマやテーブル名（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を事前に準備してください（DuckDB / SQLite）。
- OpenAI を使う機能は API コストとレート制限に注意。ローカルテスト時は環境変数に API キーをセットするか、score_news/score_regime の api_key 引数で明示的に渡してください。
- 自動で .env を読み込む処理はプロジェクトルート検出に .git または pyproject.toml を用います。CI / テスト時に自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 参考・注記

- 本 README はソースコードに基づく概要ガイドです。各モジュールの詳細な引数仕様・戻り値はソース内の docstring を参照してください（関数ごとに丁寧にコメントが付与されています）。
- 実運用前に以下を必ず実施してください：
  - テスト環境（paper_trading）での総合テスト
  - リスク制限値（ドローダウン閾値、ポジション上限、CPU/メモリ閾値など）の調整
  - OpenAI / ブローカー API キーの安全な管理

---

必要であれば、具体的なセットアップスクリプト（requirements.txt / pyproject.toml の生成）、起動サンプルスクリプト群、よく使う SQL スキーマ定義の抜粋なども作成します。どれを優先して出力しましょうか？