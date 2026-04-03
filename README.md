# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買（バックテスト / リサーチ / 実運用支援）を目的とした Python ライブラリです。  
本リポジトリはデータ取得・ETL・品質チェック、ニュース NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注トレース）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（関数は内部で date.today() に依存しない等）
- DuckDB を使ったローカルデータ管理と冪等保存（ON CONFLICT）
- OpenAI（gpt-4o-mini）を用いた JSON Mode による安定的な NLP 評価
- API 呼び出しに対するリトライ・レート制御を実装
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化等）

---

## 機能一覧

- 環境変数 / .env 読み込み（自動ロード機能）
- J-Quants API クライアント（株価・財務・マーケットカレンダー取得、トークンリフレッシュ・レート制御・リトライ）
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev trading day）
- ニュース収集（RSS → raw_news、SSRF 対策、テキスト前処理）
- ニュース NLP（銘柄ごとのセンチメントスコア算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー など）
- 研究用ユーティリティ（将来リターン計算、IC / 統計サマリ、Zスコア正規化）
- 監査ログスキーマ初期化（signal / order_request / executions 等のテーブル・インデックス）
- DuckDB ベースの監査 DB 初期化ユーティリティ

---

## 前提（Prerequisites）

- Python 3.10+
- DuckDB（pip パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（XML の安全パース）
- その他標準ライブラリ（urllib 等）

推奨インストール例（仮想環境内）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# さらにパッケージ管理がある場合は pyproject.toml / requirements.txt を参照して下さい
```

開発環境ではプロジェクトルートで:
```bash
pip install -e .
```
が利用できる想定です（pyproject.toml がある前提）。

---

## 環境変数（主なもの）

プロジェクトは .env / .env.local を自動で読み込みます（プロジェクトルートの .git または pyproject.toml を基準）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

必須 / 重要な環境変数例：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（運用時）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / regime 判定で使用）

任意：
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

.example `.env`（プロジェクトルートに作成）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリをインストール
   - 最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発用に pyproject.toml / requirements.txt があればそれを使用

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数をエクスポートしてください。
   - 自動ロードを無効にしたい場合は環境で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. DuckDB ファイル用フォルダ作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリの代表的な使い方例です。実運用ではログ設定や例外ハンドリング、API キー管理を適切に行ってください。

- DuckDB 接続を作成して ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（特定日）のスコア算出
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {num_written}")
```
score_news は OPENAI_API_KEY を環境変数に持っていることを前提とします。引数 api_key に直接渡しても可。

- 市場レジーム判定（regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対してアプリは order_requests / executions などを書き込む
```

- J-Quants クライアントで株価取得（単発）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を持つ dict のリスト
```

---

## CLI / ジョブ運用（例）

本パッケージは CLI を提供していない（本コード断片では）想定ですが、上記の Python API を使って cron / systemd タイマー から以下のように呼び出すことができます。

- 日次 ETL（深夜バッチ）
- ニュース収集 → score_news（朝スコアリング）
- regime_detector の定期実行（朝のマーケットオープン前）

ジョブの実行例（簡易スクリプト）:
```bash
python -c "from datetime import date; import duckdb; from kabusys.data.pipeline import run_daily_etl; print(run_daily_etl(duckdb.connect('data/kabusys.duckdb'), date.today()).to_dict())"
```

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                     -- 環境変数 / .env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュース NLP（銘柄別 ai_scores 書込）
  - regime_detector.py          -- 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py      -- カレンダー（営業日判定等）
  - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
  - etl.py                      -- ETLResult 再エクスポート
  - stats.py                    -- 共通統計ユーティリティ（zscore_normalize）
  - quality.py                  -- データ品質チェック
  - audit.py                    -- 監査ログスキーマ初期化
  - jquants_client.py           -- J-Quants API クライアント（fetch/save）
  - news_collector.py           -- RSS 収集（SSRF 対策・前処理）
- research/
  - __init__.py
  - factor_research.py          -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py      -- 将来リターン・IC・統計サマリ
- research/*, data/* のテストユーティリティや追加モジュールがプロジェクトに存在する可能性あり

パッケージ外（プロジェクトルート）:
- .env, .env.local               -- 環境変数（プロジェクトルートに配置）
- pyproject.toml / requirements.txt (存在する場合)

---

## 注意点 / 運用上の留意事項

- 機密情報（J-Quants / OpenAI / kabu API トークン）は絶対に公開リポジトリに置かないでください。
- OpenAI API コールはコストとレート制限が発生します。batch サイズやリトライの挙動に注意してください。
- ETL のデータ整合性・品質チェックは自動化されていますが、初期導入時はログを確認し、quality_issues を確認してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン差異を考慮した実装が含まれています。運用時は duckdb パッケージのバージョン管理を行ってください。
- 自動 .env ロードはプロジェクトルートを基準に .git または pyproject.toml を探します。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## 開発 / 貢献

- まず Issue を作成して実装方針を相談してください。
- コードスタイルは PEP8 準拠を推奨します。
- テストは重要（ETL / API ラッパー / NLP の外部呼び出しはモックでテストすること）。

---

不明点や追加で README に載せたい内容があれば教えてください。必要に応じて README にサンプル .env.example、より詳細なジョブスケジュール例、ユニットテスト実行手順などを追記します。