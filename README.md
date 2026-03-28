# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ（発注/約定のトレース）、市場カレンダー管理、及び AI を使った市場レジーム判定などのユーティリティを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、上場銘柄情報、JPXカレンダーの差分取得と DuckDB への保存（冪等保存）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS フィードの収集、前処理、raw_news テーブルへの冪等保存、銘柄紐付け
  - SSRF 対策、サイズ上限、トラッキングパラメータ除去などの防御処理
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini を想定）を用いたニュースセンチメント解析（銘柄ごとの ai_score を ai_scores テーブルへ保存）
  - マクロニュースを活用した市場レジーム判定（ETF 1321 の MA200 乖離と LLM センチメントの合成）
  - 再試行・フェイルセーフ実装、レスポンス検証ロジック
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ
- カレンダー管理
  - market_calendar のバッチ更新、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - カレンダーデータがない場合の曜日フォールバック実装
- 監査ログ（監査テーブル）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化用ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ運用
- 設定管理
  - .env ファイル / 環境変数からの自動読み込み（パッケージルート検出）と厳格な必須チェック（Settings オブジェクト）

---

## 必要要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトがパッケージ化される際は requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. パッケージをインストール（編集可能インストール）
   ```
   pip install -e .
   ```

4. 必要パッケージを手動でインストール（プロジェクト依存に応じて）
   ```
   pip install duckdb openai defusedxml
   ```

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

6. 代表的な環境変数（.env に記載する例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベースパス（省略時 default）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作環境 / ログレベル
   KABUSYS_ENV=development   # development|paper_trading|live
   LOG_LEVEL=INFO           # DEBUG|INFO|WARNING|ERROR|CRITICAL
   ```

---

## 使い方（主な API と実行例）

※ すべての操作は DuckDB 接続オブジェクト（duckdb.connect(...) が返す接続）を渡して実行します。

- 設定にアクセスする
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB に接続
  ```python
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー・日次株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written scores: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB の初期化（監視用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring.db")  # ディレクトリ自動作成
  ```

- リサーチ / ファクター計算の呼び出し例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

注意点:
- OpenAI の API キーは環境変数 OPENAI_API_KEY か、score_news/score_regime の api_key 引数で指定できます。
- J-Quants トークンは settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）で必須です。
- ETL では DuckDB 内の各テーブルスキーマ（raw_prices / raw_financials / market_calendar / ...）が前提なので、最初にスキーマ初期化が必要な場合はドキュメント／スクリプトに従って初期化してください（サンプルスキーマは codebase に基づき作成できます）。

---

## 主要ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）スコアリング
    - regime_detector.py     — 市場レジーム判定（1321 MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログ（監査テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計概要など

（README では主要ファイルのみ記載しています。実際のツリーはリポジトリ内を参照してください。）

---

## 設定・運用に関する補足

- .env の自動ロード
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - テスト等で自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境に依存する機能
  - OpenAI（LLM）呼び出し、J-Quants API、Slack 通知等はそれぞれ有効なキー / トークンが必要です。テスト時は API 呼び出しをモックすることを推奨します。
- 安全性とフェイルセーフ
  - ニュース収集は SSRF 対策、受信サイズ上限、defusedxml を使った XML パース等を行います。
  - API 呼び出しは 429 / ネットワーク断 / 5xx を指数バックオフでリトライし、最終的に失敗しても処理を継続する（フェイルセーフ設計）箇所が多くあります。
- ログと動作モード
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定します。live では発注・実口座周りに十分注意してください。
  - LOG_LEVEL でログの閾値を調整します。

---

## よくある操作（Checklist）

- 開発時
  - 仮想環境を用意して依存をインストール
  - .env.example を元に .env を作成（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等を設定）
- 運用（本番）
  - KABUSYS_ENV=live を設定（本番発注ロジックを有効化する箇所がある場合）
  - 秘密情報は環境変数管理（Vault 等）を推奨
  - 監査 DB（init_audit_db）を用いて発注/約定のトレーサビリティを確保

---

不明点や追加で README に含めたい内容（例: データベーススキーマ定義、CI / テスト実行コマンド、依存バージョンの固定）があれば教えてください。README をそれに合わせて拡張します。