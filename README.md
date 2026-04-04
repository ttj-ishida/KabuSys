# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（約定トレーサビリティ）など、売買システム作成に必要な共通機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能群を提供します。

- J-Quants API 経由での市場データ取得（株価日足、財務データ、カレンダーなど）
- DuckDB を用いた ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_scores）およびマクロセンチメントを用いた市場レジーム判定
- 研究用途のファクター計算・特徴量探索（モメンタム / ボラティリティ / バリュー等）
- 監査ログ（signal → order_request → execut ions）用スキーマ生成ユーティリティ
- 設定管理（.env 自動ロード、環境変数取得ラッパー）

設計上の共通方針として、バックテスト等での Look‑ahead バイアスを防ぐために「現在時刻の直接参照を避ける」実装になっています（関数は target_date を受け取る等）。

---

## 機能一覧（要約）

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）、個別 ETL ジョブ
  - news_collector: RSS 取得・前処理（SSRF 対策・トラッキング除去）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: JPX カレンダーの管理と営業日判定ユーティリティ
  - audit: 監査ログ（シグナル／発注／約定）用スキーマ初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを LLM で銘柄別にスコア化して ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime を書き込む
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提条件・依存関係

- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

（プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください。）

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリのクローン（または package を配置）
2. 仮想環境を作成して有効化（任意）
3. 依存パッケージをインストール
   - pip / poetry 等を使用
4. 環境変数を設定（.env をプロジェクトルートに置けば自動で読み込まれます）

重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合に必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : execution 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL : ログレベル ("DEBUG"/"INFO"/"WARNING"/...)

.env の自動ロードについて:
- パッケージはプロジェクトルート（.git または pyproject.toml のある階層）を基準に `.env` → `.env.local` の順に自動ロードします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。実行前に必要な環境変数（特に J-Quants / OpenAI）を設定してください。

- DuckDB 接続作成（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場データ・財務・カレンダー・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n_written} symbols")
```

- 市場レジーム判定（1321 ETF の MA200 とマクロセンチメントを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブル作成済みの DuckDB 接続を返します
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- ニュース RSS を取得（保存ロジックと組み合わせて利用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# 取得記事を前処理して DB に保存する処理を組み合わせてください
```

注意:
- AI 関連関数は OpenAI API 呼び出しを行います。テスト時は各モジュールの内部呼び出し（_call_openai_api 等）をモックすることで外部 API 依存を排除できます。
- ETL / 保存処理は冪等性を保つように設計されています（DuckDB 側で ON CONFLICT DO UPDATE を使用）。

---

## 設定（.env の例）

以下は .env に設定する主要項目の例（実際の値は各自の環境に合わせてください）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

主要モジュールとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数 / .env ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュースセンチメント解析, score_news
    - regime_detector.py    -- 市場レジーム判定, score_regime
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（fetch/save）
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                -- ETLResult 再エクスポート
    - news_collector.py     -- RSS 収集・前処理
    - quality.py            -- 品質チェック
    - stats.py              -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py-- マーケットカレンダーの取得・判定ロジック
    - audit.py              -- 監査ログスキーマ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    -- モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py-- 将来リターン / IC / 統計サマリ
  - research/... (その他研究用ユーティリティ)

補足:
- docs / DataPlatform.md / StrategyModel.md 等の参照設計書に従った実装が各モジュール内にコメントで記載されています。

---

## 開発・テスト上の注意

- OpenAI 呼び出しや外部 API 呼び出しはモックしてテストしてください（各モジュール内で _call_openai_api 等を patch することを想定）。
- DuckDB を使ったテストは ":memory:" 接続を利用できます（init_audit_db(":memory:") 等）。
- settings はモジュール import 時に .env を自動ロードします。テストで自動ロードを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ライセンス / 貢献

（プロジェクトのライセンス情報や貢献ガイドラインがあればここに記載してください）

---

README はまず導入と実行例、主要 API の使い方に重点を置いています。各モジュールの詳細な仕様や SQL スキーマ、プロダクション運用に関する注意点（OpenAI 利用料、J-Quants レートリミット、機密情報管理など）はコード内の docstring を参照してください。質問や追加のドキュメント化したい箇所があれば教えてください。