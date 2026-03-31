# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリ。  
J-Quants / kabuステーション / OpenAI を利用した ETL、ニュース NLP、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するためのモジュール群です。主な役割は以下の通りです。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- RSS ニュース収集と OpenAI によるニュースセンチメント解析（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA とニュースセンチメントを合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- 発注・約定に関する監査ログスキーマの初期化（トレーサビリティ保護）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 環境設定管理（.env 自動ロード等）

設計上の特徴として、ルックアヘッドバイアスの排除に注意し、API 呼び出しのリトライやフェイルセーフ動作（API 失敗時のフォールバック）を多用しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ID トークン自動更新）
  - pipeline: 日次 ETL（差分取得、保存、品質チェック）と個別 ETL ジョブ
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS からのニュース収集（SSRF 対策・トラッキング除去・前処理）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 発注・約定の監査ログスキーマ初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Z スコア正規化等）
- ai
  - news_nlp.score_news: ニュースを OpenAI に送り銘柄別センチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離 + マクロニュースの LLM センチメントで市場レジーム判定
- research
  - factor_research: モメンタム / バリュー / ボラティリティのファクター計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリー / ランク関数
- config
  - Settings: 環境変数から各種設定を取得（.env 自動ロードあり）

---

## 要件

- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml

（実行環境に合わせて requirements.txt を用意してください。urllib 等は標準ライブラリを使用しています。）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須の環境変数は下記参照。
5. 実行に必要な DB ディレクトリ作成（例: data/）
   - mkdir -p data

---

## 環境変数

主に以下の環境変数を使用します。必須のものはアプリ側で _require によりチェックされます。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注用途）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack の投稿先チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用されます）

任意 / デフォルトあり:
- KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live") デフォルト "development"
- LOG_LEVEL             : ログレベル ("DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL") デフォルト "INFO"
- DUCKDB_PATH           : DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用途の sqlite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値があれば無効化）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表例）

以下は Python REPL やスクリプトでの利用イメージです。DuckDB 接続には `duckdb.connect(settings.duckdb_path)` 等を使用します。

1) ETL（日次パイプライン）の実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ DB 初期化（監査専用 DB を用いる場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 必要に応じてこの conn を使って監査テーブルへ書き込み可能
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の辞書リスト
```

注意点:
- 関数群は基本的に DuckDB 接続を受け取り、DB 内の特定テーブル（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）を参照・更新します。事前にスキーマ作成やテーブル初期化が必要です（ETL 実行時に必要なテーブルがなければエラーになる可能性があります）。
- OpenAI 呼び出しはエラー時にフォールバック（スコア 0）する等のフェイルセーフを持ちますが、API キーは必須です。

---

## ディレクトリ構成

提供されている主なファイルとモジュール構成は以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割は上記「主な機能一覧」を参照してください。

---

## 実運用・注意事項

- 安全性:
  - news_collector は SSRF 対策（ホストプライベート検査、リダイレクト検査）や XML の安全パーサ（defusedxml）を利用しています。
  - jquants_client はレート制御とリトライ、401 時のトークン自動更新を実装しています。
- ルックアヘッドバイアス:
  - 多くの処理は date 引数に基づいて過去データのみを参照するよう設計されており、datetime.today()/date.today() を内部で直接参照しない方針です（ただし ETL の既定動作では date.today() を使います）。
- DB スキーマ:
  - audit.init_audit_schema 等で監査用テーブルを冪等に作成できます。その他のテーブル（raw_prices 等）は ETL やスクリプト側で初期化してください。
- テスト:
  - OpenAI / ネットワーク系の呼び出しはモック可能な設計（内部 _call_openai_api を差し替える等）になっています。

---

## 貢献・ライセンス

この README ではライセンスや貢献フローの定義は含めていません。公開・共有する場合は LICENSE の追加や PR 手順のドキュメント化を推奨します。

---

必要であれば、README にサンプル .env.example、requirements.txt の推奨内容、より詳細な DB スキーマ（CREATE TABLE 文）や運用手順（cron / Airflow での ETL スケジューリング、Slack 通知のサンプル）を追加します。どの部分を詳しくしたいか教えてください。