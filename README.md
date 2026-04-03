# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。  
DuckDB ベースのデータレイク、J-Quants からの ETL、ニュース収集と LLM を使ったニュースセンチメント評価、ファクター計算、監査ログ（オーダー／約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を直接参照しない等）
- DuckDB を中心とした軽量なオンディスク DB
- J-Quants / OpenAI / kabu ステーション等外部 API は疎結合かつリトライ・レート制御付きで扱う
- ETL / 品質チェック / 監査ログは冪等（idempotent）設計

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX のマーケットカレンダー取得（jquants_client）
  - 差分取得・バックフィル・保存（pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（data.quality）
- ニュース収集・NLP
  - RSS からのニュース収集（news_collector.fetch_rss）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（ai.news_nlp.score_news）
  - マクロニュース + ETF MA に基づく市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等の計算（research.factor_research）
  - 将来リターン計算・IC 計算・統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化（data.audit.init_audit_schema / init_audit_db）
- 設定管理
  - .env ファイルおよび環境変数の自動読み込み（config.Settings）
  - 実行環境（development / paper_trading / live）、ログレベル等の集中管理

---

## 必要な環境変数

主に以下を設定してください（以外にも設定項目あり、config.Settings を参照してください）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for jquants_client）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を使う場合）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携を使う場合）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

自動読み込み:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点として
  - `.env`（優先度低）
  - `.env.local`（優先度高、既存環境変数を上書き可能）
が自動的にロードされます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール  
   以下は本プロジェクトで使用されている主要ライブラリ例です。実プロジェクトでは requirements.txt / pyproject.toml を参照してください。
   ```
   pip install duckdb openai defusedxml
   ```
   （必要に応じて urllib を使うため標準ライブラリで足ります。その他テスト用モックやロギング関連パッケージを追加してください）

4. プロジェクトを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数を設定（.env を作成するか、CI/システムの環境変数に設定）
   - JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等を設定

---

## 使い方（主要なユースケース）

以下は簡単な Python スニペット例です。事前に DuckDB と環境変数が設定されていることを前提とします。

- DuckDB 接続を作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（全データ取得 + 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を計算して ai_scores に書き込む:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていると api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム（bull/neutral/bear）を判定して market_regime テーブルに保存:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（audit）データベースを初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- RSS を取得して raw_news に保存するワークフローの一部（fetch_rss を使って戻り値を処理）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
# DB へ保存するユーティリティはプロジェクト内に組み込めます（省略）
```

注意点:
- OpenAI の呼び出しは API 料金が発生します。テスト時はモック化を推奨します（各 ai モジュールは _call_openai_api をモック可能に設計されています）。
- J-Quants API 呼び出しはレート制御／リトライ実装がありますが、正しいトークン（JQUANTS_REFRESH_TOKEN）を設定してください。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 配下の主要モジュールと簡易説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理・自動 .env 読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py       : ニュースの LLM センチメント評価・ai_scores への書き込み
    - regime_detector.py: ETF MA とマクロセンチメントを合成して market_regime を作成
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得＋DuckDB 保存）
    - pipeline.py       : ETL パイプライン（run_daily_etl 等）
    - etl.py            : ETLResult 再エクスポート
    - news_collector.py : RSS 取得・前処理（SSRF 対策・XML サニタイズ）
    - calendar_management.py : 市場カレンダー管理・営業日計算
    - quality.py        : データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py          : zscore_normalize 等統計ユーティリティ
    - audit.py          : 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     : モメンタム／バリュー／ボラティリティの計算
    - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - research パッケージ: ファクターリサーチ用ユーティリティ群
  - その他: strategy / execution / monitoring 等（パッケージ公開用 __all__ に含まれるが実装は別途）

（注）ファイル群は README 作成時点の抜粋です。プロジェクトにより追加モジュールやスクリプトが含まれる可能性があります。

---

## 開発・テストのヒント

- 各外部 API 呼び出し（OpenAI、J-Quants、RSS のネットワークアクセス）はモックしやすいように分割された実装になっています。ユニットテストではモック化して安定したテストを行ってください。
- DuckDB をテストで使用する場合、":memory:" を使うとインメモリ DB が得られます（data.audit.init_audit_db などは ":memory:" に対応）。
- ai モジュールは外部呼び出しの失敗時に安全側のフォールバック（例: macro_sentiment=0.0）を行うため、本番実行時に API エラーが発生してもプロセス全体が停止しない設計です。ただし、ログを必ず確認してください。

---

## ライセンス / 貢献

この README はコードベースのドキュメント生成に基づいて作成しています。実際のライセンスや貢献フロー（CONTRIBUTING.md）がリポジトリに含まれている場合はそちらを優先してください。

---

不明点や追加で README に載せたいセクション（例: CLI 操作、Docker 化手順、具体的な .env.example の自動生成など）があれば教えてください。必要に応じて追記します。