# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants）によるデータ取得、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（監査テーブル／約定トレーサビリティ）などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から日足（OHLCV）・財務データ・上場情報・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / upsert）
  - 日次 ETL パイプライン（カレンダー -> 株価 -> 財務 -> 品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue 型で詳細を収集
- ニュース収集（RSS）
  - RSS 取得、URL 正規化（トラッキング除去）、SSRF 対策、記事IDハッシュ化、raw_news への冪等保存想定
- ニュース NLP（OpenAI）
  - gpt-4o-mini を用いた銘柄ごとのニュースセンチメント（ai_scores への書き込み）
  - レートリミット・リトライ・レスポンス検証を考慮
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定
- リサーチ用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計概要
  - z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - 監査テーブルの初期化関数（init_audit_schema / init_audit_db）
- 設定管理
  - .env / 環境変数自動ロード（プロジェクトルート検出）
  - 必須設定の取り扱い（未設定時は例外）

---

## 動作環境 / 要件

- Python 3.10 以上（型アノテーションで | を使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード等）

実際のプロジェクトでは requirements.txt / pyproject.toml を確認してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。例:
     ```bash
     pip install -r requirements.txt
     ```
   - 最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` があれば自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（必須・任意）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN (必須) — Slack 通知に使用
     - SLACK_CHANNEL_ID (必須)
     - OPENAI_API_KEY (必要な機能を使う場合)
     - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
     - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C12345678
   ```

---

## 使い方（簡単な例）

以下はライブラリを直接インポートして機能を呼び出す例です。プロダクションではスクリプトやジョブとして利用してください。

- DuckDB 接続作成（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores）をスコアリング
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化（専用ファイル）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions が作成される
  ```

- リサーチ: ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
  ```

注意:
- AI（OpenAI）を使う関数は API キーが必要です。api_key 引数に渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出し時はネットワークと外部 API のレート制限に注意してください。

---

## 主要モジュールと簡単な説明（抜粋）

- kabusys.config
  - 環境変数の自動ロードと settings オブジェクト（必須値チェック含む）
- kabusys.data
  - pipeline.py : ETL パイプライン（run_daily_etl など）
  - jquants_client.py : J-Quants API クライアント（fetch / save 関数）
  - news_collector.py : RSS ベースのニュース収集ユーティリティ
  - quality.py : データ品質チェック
  - calendar_management.py : 市場カレンダー管理と営業日計算
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログ用スキーマ定義・初期化
- kabusys.ai
  - news_nlp.py : ニュースを LLM に投げて銘柄別スコアを生成（score_news）
  - regime_detector.py : マクロセンチメント + ETF MA による市場レジーム判定（score_regime）
- kabusys.research
  - factor_research.py : Momentum / Volatility / Value のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - quality.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - audit.py
      - audit.py
      - ...（その他データ関連モジュール）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...（リサーチユーティリティ）
    - ai/ (上記)
    - research/ (上記)
- pyproject.toml / setup.cfg / requirements.txt（存在する場合）
- .env.example（存在する場合：環境変数の例）

（上記はコードベースの抜粋に基づく構成です。実際のリポジトリで差異がある場合があります。）

---

## 運用上の注意点

- Look-ahead bias を避ける設計が組み込まれています。日付計算は target_date を明示的に与えるか、ETL 内で適切に調整して使用してください。
- OpenAI 呼び出しはリトライとフォールバック（失敗時は 0.0）を備えていますが、API コストとレート制限に注意してください。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter が組み込まれていますが、大量のページネーションや並列処理時は監視してください。
- DuckDB のバージョン依存（executemany の空リストや型バインドの挙動）に注意していますが、実運用前にローカルで動作確認を行ってください。
- .env 自動読み込みはプロジェクトルート判定に __file__ を使っているため、パッケージ化後や一部テストで挙動が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードしてください。

---

## 追加情報 / テスト

- テスト用に API 呼び出し部分は内部関数を patch/mocking して差し替えられるよう実装されています（ユニットテストでの差し替えを想定）。
- ロギングはモジュールごとに logger を取得しており、LOG_LEVEL で制御できます。

---

ご不明点や README に追加したい項目（例: 実行スクリプト、CI 設定、詳細な環境変数説明など）があれば教えてください。必要に応じて .env.example のサンプルや具体的なスクリプト例を追加します。