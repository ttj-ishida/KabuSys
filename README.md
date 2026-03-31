# KabuSys

日本株向けの自動売買 / データプラットフォームコンポーネント群です。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理など、バックテスト／運用に必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄一覧、マーケットカレンダー取得
  - レート制御・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 日次差分 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損、スパイク、重複、日付整合性）

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 考慮、フラグメント・トラッキング除去、サイズ制限）
  - raw_news / news_symbols への冪等保存想定（モジュール提供）

- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースをまとめて LLM に投げ、センチメント（ai_score）を ai_scores に書き込む（score_news）
  - レート制限・リトライ・レスポンスバリデーション

- 市場レジーム判定（Regime Detection）
  - ETF（1321）200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を組み合わせて日次の市場レジームを判定（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials 利用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- 監査ログ（Audit / トレーサビリティ）
  - signal_events / order_requests / executions テーブルを作成・初期化するユーティリティ（init_audit_db / init_audit_schema）
  - UUID ベースの冪等キー・状態遷移管理

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml

例（pip）:
```bash
pip install duckdb openai defusedxml
```

※プロジェクト用途に応じてその他パッケージやバージョン制約がある場合は pyproject.toml 等を参照してください。

---

## セットアップ手順

1. レポジトリをクローン / ソースを取得
2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし requirements.txt がある場合
   pip install duckdb openai defusedxml
   ```
3. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY - OpenAI API キー（AI モジュール使用時）
     - KABU_API_PASSWORD - kabu ステーション API 用パスワード
     - KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN - Slack 通知用トークン
     - SLACK_CHANNEL_ID - Slack チャンネル ID
     - DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH - SQLite パス（監視等）
     - KABUSYS_ENV - 環境 (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース用ディレクトリ作成（必要な場合）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な API / 実行例）

以下は Python からの簡単な利用例です。DuckDB 接続は duckdb.connect() を利用します。

- ETL（日次パイプライン）を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL ジョブ（株価のみ）:
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュースの RSS 取得（fetch_rss）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- ニュースセンチメントのスコアリング（AI）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定しておくか、api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores written: {n_written}")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring.duckdb")
# tables for signal_events / order_requests / executions are created
```

- 設定値をコードから参照:
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

---

## 環境変数の自動読み込みについて

- パッケージ初期化時に、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env.local` は OS 環境変数を上書きする（override=True）仕様です。OS 環境変数は保護されます。

---

## ディレクトリ構成（主要ファイル・モジュール）

プロジェクトは src/kabusys 以下に実装されています。主要なモジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                          - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       - ニュース NLP（score_news）
    - regime_detector.py                - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 - J-Quants API クライアント（fetch / save）
    - pipeline.py                       - ETL パイプライン（run_daily_etl 等）
    - etl.py                            - ETLResult のエクスポート (ETLResult)
    - news_collector.py                 - RSS 収集 / 前処理
    - calendar_management.py            - マーケットカレンダー管理
    - quality.py                         - データ品質チェック
    - stats.py                           - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                           - 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py                - ファクター計算（momentum / value / volatility）
    - feature_exploration.py            - 将来リターン / IC / 統計サマリ

各モジュールはドキュメントストリングで詳細な設計方針・処理フロー・注意点が記載されています。まずは pipeline.run_daily_etl / ai.score_news / ai.score_regime / data.jquants_client.* / data.news_collector.fetch_rss を中心に動作確認してください。

---

## 開発上の注意点

- Look-ahead バイアス対策が各所で考慮されています（datetime.today() を直接参照しない、データ取得や計算で対象日より後のデータを使わない等）。
- OpenAI 呼び出しはリトライやフェイルセーフを備えており、API 失敗時はゼロスコアで継続する挙動をとる箇所があります（運用ポリシーに合わせて調整可能）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン差を考慮している箇所があります（パラメタが空でないことをチェックしてから実行）。

---

## サポート / 拡張ポイント

- 新しい RSS ソースの追加、ニュース → 銘柄紐付けロジックの改善
- AI モデルやプロンプトの改良（モデル名は定数で管理）
- 追加の品質チェックやアラート（Slack 連携）
- kabu ステーションとの実際の発注フロー（execution モジュール未提供部分の実装）

---

README はここまでです。リポジトリ内の doc や各モジュールの docstring を参照すると、関数の引数・戻り値・例外挙動など詳細が得られます。必要であれば利用例や運用手順（Cron / Airflow / GitHub Actions などでの定期実行）のテンプレートも作成します。どの部分を優先して追加すればよいか教えてください。