# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースセンチメント（LLM）、市場レジーム判定、監査ログ、データ品質チェック、ファクター計算などを提供します。

主に DuckDB ベースでデータを保持し、J-Quants API や RSS、OpenAI（gpt-4o-mini）を用いた処理を行います。

---

## 主要機能

- データ取得・ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得して DuckDB に保存（冪等性を保持）
  - ETL の結果を表す ETLResult を提供
- データ品質チェック
  - 欠損、スパイク（異常値）、重複、日付不整合などの検出
- ニュース収集
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存（SSRF 対策、トラッキング除去、ファイルサイズ制限）
- ニュース NLP（LLM）
  - OpenAI を用いた銘柄別ニュースセンチメント（ai_scores テーブルへの保存）
  - バッチ処理・リトライ・レスポンス検証を備えた実装
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を算出・保存
- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ランク付け、統計サマリー
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブルを DuckDB に初期化
- 環境設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（パッケージ配布後でも .git や pyproject.toml を基にルートを探索）
  - 必須項目のチェック（未設定時は ValueError）

---

## 動作環境（推奨）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）

※ 実行環境に合わせて requirements.txt を用意してください。上記パッケージは最低限必要になります。

---

## 環境変数 / 設定

kabusys.config.Settings で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード（戦略実行 / 注文モジュールで使用）
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID
- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)  
  有効値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)  
  有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動で .env と .env.local をプロジェクトルートから読み込みます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 例: pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれに従う
4. 環境変数を設定（.env をプロジェクトルートに配置）
5. (任意) DuckDB の初期スキーマ作成や監査 DB の初期化
   - 監査ログ DB 初期化例は後述

---

## 使い方（簡単な例）

以下の例は Python スクリプト / REPL での呼び出し例です。

- DuckDB 接続準備（デフォルトパスを利用）
```python
from kabusys.config import settings
import duckdb

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックを順に実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_kabusys.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- RSS を直接取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"], a["url"])
```

注意点:
- OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、関数引数 api_key に渡してください。
- LLM 呼び出しはリトライ・フェイルセーフ処理を行いますが、API 制限やコストに注意してください。
- DuckDB の executemany は古いバージョンで空リストを嫌うため、コード側で空チェックが入っています。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py              -- ニュースセンチメント（OpenAI）
    - regime_detector.py       -- 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - etl.py                   -- ETLResult の再エクスポート
    - news_collector.py        -- RSS 収集（SSRF 対策・パース・正規化）
    - calendar_management.py   -- 市場カレンダー操作（営業日判定等）
    - stats.py                 -- 統計ユーティリティ（zscore_normalize）
    - quality.py               -- データ品質チェック
    - audit.py                 -- 監査ログ（DDL / init 関連）
  - research/
    - __init__.py
    - factor_research.py       -- Momentum / Value / Volatility 等
    - feature_exploration.py   -- 将来リターン・IC 等

---

## 実装上の注意・設計方針（抜粋）

- Look-ahead bias を避ける設計
  - 日付処理で内部的に datetime.today()/date.today() を不用意に使わず、ETL/解析関数は target_date を明示的に受け取る
  - prices_daily などのクエリは target_date 未満/以前などルックアヘッドを防ぐ条件を採用
- 冪等性（idempotent）を重視
  - DuckDB への保存は ON CONFLICT DO UPDATE を用い、再実行で重複を排除
- フェイルセーフ
  - LLM / 外部 API エラー時はゼロやスキップで継続できるようにし、致命的でない限り全処理を止めない
- セキュリティ
  - RSS の取得では SSRF 対策、受信サイズ制限、defusedxml を用いた XML パース

---

## 開発・テスト用メモ

- OpenAI 呼び出し部分は内部で _call_openai_api を用いており、ユニットテストではこの関数を patch して API 呼び出しをモックできます。  
  例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp)
- 自動 .env 読み込みを無効化してテストを行うには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- DuckDB を使った単体テストでは ":memory:" を使ってインメモリ DB を初期化できます（audit.init_audit_db でも対応）。

---

この README はプロジェクトの主要点をまとめたものです。実行・運用には J-Quants / OpenAI の API キーや適切な設定が必要です。詳細な API フィールド、DB スキーマや運用手順はソースコード内の docstring（各モジュールヘッダ）を参照してください。