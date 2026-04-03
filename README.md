# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリ。  
DuckDB をデータレイヤに、J-Quants からのデータ取得・ETL、ニュース収集・NLP（OpenAI）を組み合わせ、研究（ファクター算出）・監査ログ・実行監視などの機能を提供します。

主な目的は「バックテストに耐えるデータ基盤」と「実運用に必要な監査・発注トレーサビリティ」を両立させることです。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 読み込み・設定管理（自動ロード機能付き）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - トークン自動リフレッシュ、レートリミット・リトライ対応
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（run_daily_etl）
  - カレンダー・株価・財務の差分取得／保存、品質チェック
  - ETL 結果を ETLResult で返却
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化）
- ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコアリング（score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成 → score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの初期化・管理
  - 監査用 DuckDB 初期化ユーティリティ
- 市場カレンダー管理（営業日判定、next/prev/get_trading_days、夜間バッチ更新）

---

## 動作要件（推奨）

- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ requirements.txt はリポジトリにない場合があるため、必要なパッケージを pip で個別にインストールしてください。

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 開発用に editable install:
     ```bash
     git clone <repo-url>
     cd <repo>
     python -m pip install -e .
     ```

2. Python パッケージをインストール（上記参照）

3. 環境変数 / .env を準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 必須環境変数（例）
   - J-Quants API
     - JQUANTS_REFRESH_TOKEN=<your_refresh_token>
   - OpenAI（score_news/score_regime 実行時）
     - OPENAI_API_KEY=<your_openai_api_key>
   - kabu（実行・発注を行う場合）
     - KABU_API_PASSWORD=<password>
     - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
   - その他（任意 / 監視・DB パスなど）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV in {development, paper_trading, live}
     - LOG_LEVEL in {DEBUG, INFO, WARNING, ERROR, CRITICAL}

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下はライブラリの主要な機能を呼び出す最小サンプルです。実運用では例外処理やロギング、環境設定に注意してください。

1) DuckDB 接続と ETL 実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントのスコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai_scores")
```
- OPENAI_API_KEY 環境変数が設定されていれば api_key 引数は不要。テスト時は api_key を明示的に渡せます。

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

5) RSS フィード取得（ニュース収集のユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 設定（環境変数の一覧）

主な環境変数（Settings で取得されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 if using kabu station API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (score_news / score_regime 実行時に必要)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: 開発モード / ペーパートレード / ライブ (development | paper_trading | live)
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。CI／テストで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発向けヒント

- OpenAI API 呼び出し部分はリトライやフォールバック（失敗時に 0.0 を返す）を備えていますが、API レスポンスの形式変更に注意してください。
- ETL 実行は各ステップで例外を捕捉して続行する設計です。ETLResult にエラーや品質問題が集約されるため運用時はこれを監視してください。
- news_collector モジュールは SSRF 対策や XML 攻撃対策（defusedxml）を実装しています。外部 RSS を追加する際は source 名と URL を DEFAULT_RSS_SOURCES に登録するか、独自で渡してください。
- DuckDB スキーマ周り（監査テーブル等）は冪等で作成されます。テストでは ":memory:" を使って init_audit_db(":memory:") で一時DBが作れます。

---

## ディレクトリ構成（主要ファイルとサブモジュールの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの時間ウィンドウ計算、OpenAI を用いた銘柄別センチメントスコア化（score_news）
    - regime_detector.py
      - ETF (1321) の MA200 乖離とマクロニュース（LLM）を合成して日次の市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch / save 関数群
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）と ETLResult
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - news_collector.py
      - RSS 取得・正規化・前処理、raw_news 保存向けユーティリティ
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - etl.py
      - ETLResult 再エクスポート
    - audit.py
      - 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・バリュー・ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank
  - monitoring/ (宣言されているが実装ファイルはこのスニペットに含まれていない可能性あり)
  - data/（上記参照）

（README で示した以外にも補助モジュールやユーティリティが含まれます）

---

## ライセンス・貢献

- ライセンス情報がリポジトリにある場合はそれに従ってください。コントリビューションはプルリクエスト／イシューで受け付けます。
- セキュリティに関する報告はプライベートにお願いします（README に連絡先が無ければリポジトリ管理者へ）。

---

この README はコードベースの主要機能と使い方をまとめたものです。実際の運用では適切なシークレット管理（Vault など）、監視・アラート、テスト環境での検証を強く推奨します。必要であれば、各機能（ETL、AI、監査、news_collector 等）ごとの詳細ドキュメントやサンプルを追加で作成します。