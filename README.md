# KabuSys

日本株向け自動売買 / データ基盤ライブラリセット。ETL、ニュース収集・NLP、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、アルゴリズムトレード基盤でよく使う機能群を含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージ群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分ETL
- RSS を使ったニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- ETF（1321）200日MA を用いた市場レジーム判定（MA と マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用の DuckDB スキーマ初期化

設計上の特徴：
- DuckDB をデータストアに利用（オンプレ・ローカル向けに高速）
- Look-ahead bias を避ける設計（内部で date.today() に依存しない箇所が多数）
- 冪等保存（ON CONFLICT DO UPDATE / INSERT … DO NOTHING）を重視
- 外部 API 呼び出しに対してリトライ・バックオフ・レート制御を実装

---

## 主な機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS パース・前処理・SSRF対策）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄別センチメント）
  - 市場レジーム判定（score_regime：ETF MA とマクロセンチメントの合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 必要環境 / 依存

- Python 3.10+
  - （ソース内で X | Y 型アノテーションを使用しているため 3.10 以上を推奨）
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

pip インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt があればそれを利用してください）

---

## 環境変数（必須 / 重要）

このパッケージは .env / 環境変数から設定を読み込みます（config.Settings）。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（発注等で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY — OpenAI 呼び出し（score_news / score_regime）。関数引数で上書き可能。
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — valid: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

.env の例（最低限の例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

config.Settings は未設定の必須項目を読み込むと ValueError を投げます。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境作成・アクティベート
3. 必須ライブラリをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（.env.example を参考に）
5. DuckDB DB ファイルの初期化（必要に応じて）
   - 監査 DB 初期化例（監査テーブルを作る）:

```python
import duckdb
from kabusys.data.audit import init_audit_db, init_audit_schema

# ファイルベース DB を作成して監査スキーマを初期化
conn = init_audit_db("data/audit.duckdb")
# または既存接続に対して
# conn = duckdb.connect("data/kabusys.duckdb")
# init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的な呼び出し例）

以下はパッケージの関数を直接呼び出す例です。CLI は用意されていないため Python スクリプトやジョブランナーから呼び出して利用します。

1) DuckDB 接続を作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（J-Quants からデータ収集 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別）を算出して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# APIキーは環境変数 OPENAI_API_KEY を使うか、引数で渡せます
n_written = score_news(conn, target_date=date(2026,3,20))
print("written:", n_written)
```

4) 市場レジーム判定を実行（ETF 1321 の MA とマクロセンチメント合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026,3,20))
print("result:", res)
```

5) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentums = calc_momentum(conn, target_date=date(2026,3,20))
values = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

6) データ品質チェックを走らせる
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点：
- OpenAI 呼び出し系（score_news, score_regime）は環境変数 OPENAI_API_KEY、または api_key 引数で key を渡す必要があります。API 呼び出しはリトライやフォールバックを備えていますが、未設定だと ValueError を送出します。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN を使用して id_token を取得します。

---

## 自動環境読み込みの挙動

- パッケージ import 時にプロジェクトルート（.git か pyproject.toml を基準）を探索し、`.env` を読み込みます（優先度: OS 環境 > .env.local > .env）。
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてからインポートしてください（テストで有用）。

---

## よくある運用ワークフロー例

- 夜間バッチ（Cron / Airflow 等）:
  1. run_daily_etl をスケジュール実行して prices/financials/calendar を更新
  2. news_collector で RSS を収集して raw_news を更新
  3. score_news を実行して ai_scores を更新
  4. score_regime を実行して market_regime を更新
  5. 戦略が signal を生成 → order_requests → 発注ロジック（kabu API 等）

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py         -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（fetch/save）
    - pipeline.py                -- ETL 実装（run_daily_etl 等）
    - calendar_management.py     -- マーケットカレンダー管理
    - news_collector.py          -- RSS ニュース収集・前処理
    - quality.py                 -- 品質チェック
    - stats.py                   -- 統計ユーティリティ（zscore_normalize）
    - audit.py                   -- 監査ログスキーマ初期化
    - etl.py                     -- ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py         -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py     -- forward returns, IC, summaries
  - research/*（その他補助モジュール）

---

## 注意事項 / 運用時のヒント

- DuckDB の executemany に空リストを渡すとバージョン依存で例外になる箇所があるため、コード中で慎重に空チェックがされています。スクリプト側でも空データを書き込まない工夫を推奨します。
- OpenAI 呼び出しにはレート・エラー対策が入っていますが、運用環境の API クオータに注意してください。
- J-Quants の API レート制御は固定間隔スロットリング（120 req/min）で制御されます。大量取得時は時間がかかります。
- コードは Look-ahead Bias を避ける方針で実装されています。バックテスト等で利用する場合は、必ず「当時点で利用可能だったデータのみ」を用いる運用を行ってください（取得時間 / fetched_at を意識すること）。

---

必要であれば README に含めるサンプル .env.example、CI 実行方法、より詳細な API の使用例（kabu 発注フロー等）を追加します。どの部分を詳しく載せたいか教えてください。