# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI 等を使ったデータ収集（ETL）、ニュースセンチメント（LLM）評価、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件 / 依存関係
- セットアップ手順
- 環境変数（.env）
- 使い方（サンプル）
- ディレクトリ構成（主なファイルと説明）
- 補足・注意事項

---

## プロジェクト概要

KabuSys は、日本株のデータパイプラインとリサーチ／自動売買に関連する共通処理をまとめた Python パッケージです。主な提供要素は次の通りです。

- J-Quants API 経由の差分 ETL（株価日足、財務、取引カレンダー）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価
- 市場レジーム判定（ETF + マクロニュースを統合）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付整合）
- 監査ログ用スキーマ初期化（トレーサビリティ：signal → order_request → execution）
- DuckDB を用いたローカルデータ保存

設計上の主な方針：
- ルックアヘッドバイアスを避ける（datetime.today()/date.today() の不適切な参照を避ける等）
- 冪等性（ON CONFLICT / トランザクション管理）を重視
- 外部 API 呼び出しにはリトライ / バックオフを実装
- テスト可能性を考慮（API 呼び出し箇所を差し替え可能）

---

## 主な機能一覧

- data:
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（rate limit / retry / token refresh 対応）
  - market calendar 管理・営業日判定
  - ニュース収集（RSS）と前処理（SSRF 対策、サイズ制限、トラッキング削除）
  - データ品質チェック（missing/spike/duplicates/date consistency）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - news_nlp.score_news: 銘柄別ニュースから LLM によるセンチメント評価 → ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込み
- research:
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト

---

## 必要条件 / 依存関係

推奨 Python バージョン: 3.10 以上（型ヒントに | 記法等を利用）

主な Python パッケージ（代表例）:
- duckdb
- openai
- defusedxml

開発環境では他にもテストフレームワークや linter が必要かもしれません。実行環境に合わせて requirements.txt を作成してください。

例（最低限の pip インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存をインストール
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt   # requirements.txt を用意している場合
     ```
3. プロジェクトルートに `.env`（および開発用に `.env.local`）を配置
   - config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出し、
     `.env` → `.env.local` の順で環境変数を読み込みます（OS 環境変数が優先されます）。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. DuckDB データベースの準備
   - デフォルトのパスは `data/kabusys.duckdb`（settings.duckdb_path）
   - 監査ログ専用 DB を初期化するには:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/monitoring.db")
     ```
5. 必要な環境変数を設定（下記参照）

---

## 環境変数（.env の例）

以下は本パッケージで参照される主な環境変数の例です。実運用では秘密情報管理に注意してください。

必須:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_station_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=your_openai_api_key

オプション（デフォルトあり）:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|... （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動ロード無効化）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABU_API_BASE_URL=http://localhost:18080/kabusapi

.env の簡単な例:
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=pass
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
```

config.Settings を通してコード内で参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## 使い方（サンプル）

以下は代表的な利用例です。実行前に環境変数と DB の準備を行ってください。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（LLM）を銘柄ごとに評価して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {num_written}")
```
- OpenAI API キーは引数 api_key に渡すか、環境変数 OPENAI_API_KEY を利用します。

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算・研究用ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

5) 監査ログスキーマの初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring.db")
# conn を使って order_requests / executions テーブルへ記録可能
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと役割の概要（src/kabusys 以下）。

- __init__.py
  - パッケージバージョンと公開サブパッケージ定義

- config.py
  - .env 自動読み込み、Settings オブジェクト（環境変数アクセスラッパ）

- ai/
  - news_nlp.py: ニュースの LLM センチメント評価、ai_scores への書き込みロジック
  - regime_detector.py: ETF MA とマクロニュースを合成した市場レジーム判定

- data/
  - jquants_client.py: J-Quants API クライアント（fetch/save/認証/レートリミット）
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - calendar_management.py: マーケットカレンダー管理（営業日判定等）
  - news_collector.py: RSS 収集と前処理（SSRF, サイズ制限等の防御を含む）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
  - etl.py: ETLResult 再エクスポート

- research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC, rank, 統計サマリ等

---

## 補足・注意事項

- OpenAI の呼び出しには料金が発生します。API キーの取り扱いに注意してください。
- J-Quants API の認証トークンやレート制限に関する取り扱いは jquants_client.py に従ってください（自動リフレッシュ、固定間隔スロットリング、再試行）。
- DuckDB の executemany に関する互換性や制約に注意（パッケージ内のコメント参照）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
- パッケージは「バックテストの内部ループから直接 API を呼ぶべきではない」設計が多く含まれています。データは事前に ETL で取得してから利用する方針を推奨します。

---

この README はコードベースの公開インターフェースと主要な設計方針をまとめたものです。さらに詳しい内部実装や API 使い方は各モジュールの docstring を参照してください。