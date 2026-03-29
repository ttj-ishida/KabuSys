# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 研究（ファクター計算）→ AI（ニュースセンチメント / 市場レジーム）→ 監査ログまでのワークフローをサポートします。

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン、リサーチ用ユーティリティ、AIベースのニュース解析、監査ログなどを統合した内部ライブラリです。DuckDB をデータ格納に使用し、J-Quants API から株価・財務・カレンダーを取得します。OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析や市場レジーム判定の機能も備えています。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で `date.today()` を不用意に参照しない）
- DuckDB で効率的に SQL/ウィンドウ集計を実行
- ETL / 品質チェックは部分失敗しても他処理を継続するフェイルセーフ設計
- API 呼び出しには適切なレート制御とリトライを実装

---

## 機能一覧

- 環境設定管理
  - `.env` 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ（`kabusys.config.settings`）

- データ（kabusys.data）
  - J-Quants クライアント（取得/保存/ページネーション/リトライ/トークンリフレッシュ）
  - ETL パイプライン（差分取得、バックフィル、品質チェック、日次 ETL）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS→raw_news、SSRF/サイズ/トラッキング除去対策）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログスキーマの初期化 / 監査 DB ユーティリティ

- 研究（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク付け）
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- AI（kabusys.ai）
  - ニュースセンチメント（`score_news`）：銘柄毎に AI スコアを ai_scores に書込
  - 市場レジーム判定（`score_regime`）：ETF(1321) の MA200 とマクロニュースを合成し market_regime に書込
  - OpenAI 呼び出しはモデルと JSON Mode を利用、エラー処理・リトライ実装

---

## セットアップ手順

前提
- Python 3.8+
- DuckDB をネイティブに利用できる環境
- J-Quants / OpenAI の API キー（必要に応じて）

推奨パッケージ（最低限）:
- duckdb
- openai
- defusedxml

例（pip）:
```bash
python -m pip install duckdb openai defusedxml
# 開発時:
# python -m pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能を使う場合必須）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）

.env の自動読み込みについて:
- パッケージ起点でプロジェクトルート（.git または pyproject.toml）を検出し、`.env` と `.env.local` を順に読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

セキュリティ: `.env` に秘密情報を保存する場合は Git などに絶対にコミットしないでください。

---

## 使い方（基本例）

以下は Python スクリプト / REPL での利用例です。

1) 設定と DuckDB 接続（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（株価・財務・カレンダー・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを計算して ai_scores に書き込む
（OpenAI API キーが環境変数 `OPENAI_API_KEY` に設定されていること）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジーム判定（1321 の MA200 とマクロニュースを評価し market_regime に書込）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 audit_conn を使って監査ログテーブルにアクセス可能
```

6) 市場カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

7) ニュース RSS 収集（例）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得後、DB 保存処理を行う関数を用意している想定（raw_news への保存はここで行うかラップしてください）
```

注意点:
- AI 関連関数（score_news, score_regime）は OpenAI API キーを必要とします。
- 各関数は DuckDB 接続を直接受け取ります（トランザクション管理やエラーハンドリングは呼び出し側で必要に応じて制御できます）。
- `run_daily_etl` 等の ETL は部分失敗しても他処理を継続する設計です。結果は ETLResult オブジェクトで詳細を確認できます。

---

## ディレクトリ構成（主要ファイル）

省略せず主要モジュールを列挙します（パッケージルート: `src/kabusys/`）。

- src/kabusys/
  - __init__.py
  - config.py                          # 環境設定/.env ローダ
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースセンチメント（score_news）
    - regime_detector.py                # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント + 保存関数
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - etl.py                            # ETL 公開型（ETLResult 再エクスポート）
    - calendar_management.py            # 市場カレンダー管理（is_trading_day etc.）
    - news_collector.py                 # RSS 収集
    - quality.py                        # データ品質チェック
    - stats.py                          # 統計ユーティリティ（zscore_normalize）
    - audit.py                          # 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算（momentum/value/volatility）
    - feature_exploration.py            # 将来リターン/IC/summary/rank
  - research/__init__.py
  - other modules (execution/monitoring/strategy) referenced in package __all__ may exist or be planned

---

## 開発・テストに関するメモ

- 自動 .env ロードをテストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 呼び出し部分は外部 API を使うためユニットテストではモック（例: `unittest.mock.patch`）してテストしてください。各モジュールはテスト容易性を考えて API 呼び出し関数が分離されています（内部 `_call_openai_api` など）。
- DuckDB を用いたテストは `:memory:` を渡してインメモリ DB を利用可能です（例: `duckdb.connect(":memory:")`）。
- 機密情報（API キー等）は環境変数または安全なシークレット管理で扱ってください。

---

もし README に含めたい追加の利用例（CI/CD、Docker、具体的な SQL スキーマ例、Slack 通知サンプルなど）があれば教えてください。必要に応じて追記します。