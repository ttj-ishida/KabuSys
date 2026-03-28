# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（発注 → 約定トレース）などを含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 設定（環境変数）
- 使い方（主要 API の使用例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチ用途に必要な以下の機能を提供する Python ライブラリです。

- J-Quants API を用いた株価・財務・上場情報・マーケットカレンダーの ETL
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去など）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄ごと）およびマクロセンチメントの合成による市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ（Zスコア正規化、IC 計算 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）用のスキーマ生成・初期化
- DuckDB を中心としたローカル DB 操作（ETL の保存・品質チェックなど）

設計上の特徴：
- ルックアヘッドバイアス回避に配慮（内部で date.today() を不用意に参照しない実装）
- 冪等的な DB 保存（ON CONFLICT / UPDATE を使用）
- フェイルセーフな実装（外部 API 失敗時は部分継続）
- 外部 API 呼び出しのリトライ・レート制御を実装

---

## 主な機能（一覧）

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、トークン自動リフレッシュ、レートリミット）
  - pipeline: 日次 ETL 実行（run_daily_etl など）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化 / 専用 DB 初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: マクロセンチメント + ETF MA 乖離を合成して market_regime を書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数読み込み・Settings オブジェクト
- audit / execution / monitoring（パッケージ公開名として __all__ に含められています）

---

## セットアップ手順

想定 Python バージョン: 3.10 以上（PEP 604 の型記法などを使用）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要な依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt / pyproject.toml はコードベースに依存します。プロダクションでは追加のパッケージ（logging 設定、Slack クライアント等）が必要になる場合があります。

3. 開発インストール（ソースツリー直下で）
   - pip install -e .

4. データディレクトリの初期化
   - settings.duckdb_path / settings.sqlite_path のディレクトリが自動で作成されるようにするか、手動で作成してください（多くの初期化関数は親ディレクトリを作成しますが、念のため）。

---

## 設定（環境変数）

config.Settings が必要な環境変数をラップしています。主なキー：

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注機能を使う場合）

任意（デフォルトあり）:
- KABU_API_BASE_URL : kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite パス（default: data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live （default: development）
- LOG_LEVEL : DEBUG/INFO/...（default: INFO）

OpenAI 関連:
- OPENAI_API_KEY : OpenAI を使う機能（score_news / score_regime）の API キー（関数呼び出しで api_key を渡すことも可）

.env 自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env, .env.local を自動で読み込みます（OS 環境変数の上書きルールは .env.local が優先）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意:
- config._require は未設定の必須キーに対して ValueError を投げます。README 配布時は .env.example を参考に .env を作成してください（コード内にもヒントが出ます）。

---

## 使い方（主要 API）

以下は代表的な利用例です。実行には前述の環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）が必要です。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（score_news）
- raw_news / news_symbols テーブルが事前に存在し、該当時間ウィンドウの記事がある状態で呼び出します。
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

3) 市場レジーム判定（score_regime）
- ETF コード 1321（年200日 MA 乖離）とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

注意点:
- OpenAI 呼び出し部分は外部 API に依存するため、ユニットテスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えてください（各モジュールに差し替えポイントがあります）。
- ETL / 保存処理は冪等を想定していますが、本番運用前に小規模で検証することを推奨します。

---

## ディレクトリ構成（主要ファイル）

（ src/kabusys 配下を抜粋）

- src/kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (その他 research 用ユーティリティ)
  - (strategy/, execution/, monitoring/ 等のパッケージが __all__ に想定されています)

各ファイルの責務（概略）:
- config.py: .env 自動読み込み、Settings（環境変数のラッパ）
- data/jquants_client.py: J-Quants との通信、DuckDB への保存関数
- data/pipeline.py: run_daily_etl 等の ETL ワークフロー
- data/news_collector.py: RSS 取得・記事の正規化と raw_news への保存
- ai/news_nlp.py: 銘柄ごとのニュースセンチメントを取得して ai_scores へ保存
- ai/regime_detector.py: ETF MA とマクロセンチメントを合成して market_regime を生成
- research/*: ファクター計算と統計解析ユーティリティ
- data/audit.py: 監査ログ用テーブル DDL と初期化ユーティリティ

---

## 運用上の注意

- テスト環境と本番環境（paper_trading / live）の切り替えは KABUSYS_ENV で管理します。is_live / is_paper / is_dev により判定できます。
- OpenAI API 呼び出しはコストとレート制限の対象です。API キーの管理、リトライ時のバックオフなどは既に実装されていますが、運用ポリシーを決めてください。
- J-Quants の API レート制限（120 req/min）に対応する RateLimiter を実装済みです。大量バッチ処理の際は十分に監視してください。
- raw_news / raw_prices などのスキーマは ETL 側に依存します。既存の DB スキーマがない状態で動かす場合はまず ETL を実行してテーブルを作成してください（またはスキーマ初期化用のユーティリティを用意してください）。

---

## 参考 / テストのヒント

- OpenAI など外部 API はモック化して単体テストを実行してください（各 ai モジュールは _call_openai_api を内部で呼び出すため、そこを patch するのが簡単です）。
- news_collector の RSS 取得はネットワーク/SSRF チェックを多数行います。ユニットテストでは _urlopen を差し替えてローカルのフィードを返すようにしてください。
- DuckDB はインメモリ接続（":memory:"）も利用可能です。テストでは init_audit_db(":memory:") のようにして一時 DB を使うと便利です。

---

README に含めるべき追加情報（必要に応じて）:
- pyproject.toml / requirements.txt（依存の確定）
- データベーススキーマの詳細（DDL）
- 実運用でのデプロイ手順（cron / Airflow / GitHub Actions 等）
- ライセンス情報

ご希望があれば、上記の追加項目（依存ファイルの例、.env.example、サンプル SQL スキーマ、運用ガイド）を追記します。