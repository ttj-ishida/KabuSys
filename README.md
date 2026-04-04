# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ取得（J-Quants）、ETL、ニュース収集／NLP（OpenAI）、因子計算、監査ログ、カレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ基盤と研究・自動売買のためのユーティリティ群です。主な役割は以下の通りです。

- J-Quants API からのデータ取得（株価日足 / 財務 / 上場銘柄 / 市場カレンダー）
- DuckDB を用いた ETL パイプライン（差分フェッチ、保存、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメタ除去）
- OpenAI を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 等）
- 監査ログ用スキーマ（signal / order_request / execution を冪等に記録）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）

設計上、ルックアヘッドバイアス防止を重視し、モジュールの多くは内部で `date.today()` 等を安易に参照しないようになっています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - DuckDB への冪等保存（save_*）
  - トークン自動リフレッシュ、レートリミッティング、リトライ実装

- data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - ETL 結果は ETLResult オブジェクトで集約

- data.quality
  - 欠損 / スパイク / 重複 / 日付不整合チェック（run_all_checks）

- data.news_collector
  - RSS 取得、テキスト前処理、記事ID生成（トラッキング除去、SSRF 対策）

- ai.news_nlp
  - ニュースを銘柄ごとにまとめて OpenAI に投げ、銘柄別スコアを ai_scores に書き込む（score_news）

- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム判定（score_regime）

- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC 計算、統計サマリー

- data.audit
  - 監査ログスキーマ作成・初期化（init_audit_schema / init_audit_db）

- config
  - .env 自動読み込み（プロジェクトルート基準）、設定値のラッパー（settings）

---

## セットアップ手順

前提:
- Python 3.10+（PEP 604 型注釈や | を使用しているため）
- DuckDB, OpenAI SDK 等の依存パッケージ

例: 仮想環境を作成してパッケージをインストールする

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージをインストール（プロジェクトの requirements に合わせて追加してください）
pip install duckdb openai defusedxml
# パッケージを開発モードでインストールする場合（setup.cfg/pyproject がある想定）
pip install -e .
```

環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須な機能がある場合）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（オプション）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）

.env 自動読み込み:
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は最小限の使用例です。実運用ではエラーハンドリングやロギング設定を適切に行ってください。

1) DuckDB 接続を作る / ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores テーブルに書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム判定（マクロセンチメント + ETF 1321 MA200）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/monitoring_audit.duckdb")
# conn_audit を使って order_events 等の操作が可能
```

5) RSS を取得して前処理する（news_collector のユーティリティ）

```python
from kabusys.data.news_collector import fetch_rss, preprocess_text

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    text = preprocess_text(a["title"] + " " + a["content"])
    print(a["id"], text[:200])
```

---

## 注意点 / 実装上の設計ポリシー

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で `date.today()` などを直接参照せず、呼び出し側が `target_date` を与える設計です（バックテストでの日付制御が容易）。
- API 呼び出しにはリトライ・バックオフ、レート制御を実装しています（J-Quants, OpenAI の両方）。
- DuckDB への書き込みは可能な限り冪等に（ON CONFLICT DO UPDATE / DO NOTHING）。
- ニュース収集は SSRF 対策、コンテンツ長制限、トラッキングパラメータ除去などセキュリティ考慮を行っています。
- テストを容易にするため、OpenAI の呼び出し関数や URLopen をモック差し替えられるようになっています。

---

## 環境変数と設定（まとめ）

主要な環境変数（設定は Settings クラス経由でアクセスされます）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

設定値は環境変数を通じて取得され、未設定の必須キーは ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なモジュール構成（src/kabusys 以下）:

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
    - (etl を再エクスポートする etl.py)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは z-score 正規化等のユーティリティも再公開
  - その他: strategy, execution, monitoring パッケージは __all__ に含まれる（将来的な拡張用）

（README の先頭で示したファイル群を参照してください。各モジュールに詳細なドキュメント文字列が含まれています。）

---

## 開発・デバッグのヒント

- .env の自動ロードは import 時に行われます。テスト時に自動ロードを抑制したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワークアクセス部分は unittest.mock.patch により差し替えてユニットテスト可能です（各モジュールのコメント参照）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内でガードされています。

---

## おわりに

この README はコードベースの主要機能と使い方の概要を示しています。各機能の詳細は該当モジュールの docstring（ソース内コメント）を参照してください。必要であれば、デプロイ手順、CI 設定、サンプル .env.example を追記できます。質問や追加したいドキュメント項目があれば教えてください。