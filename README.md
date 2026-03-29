# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター/リサーチユーティリティ、監査ログ（発注→約定のトレーサビリティ）等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォーム向けに設計された Python モジュール群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたローカルデータ基盤（ETL・品質チェック）
- RSS ベースのニュース収集と OpenAI による記事/マクロセンチメント評価
- ファクタ計算（モメンタム / バリュー / ボラティリティ等）とリサーチ用ユーティリティ
- 発注フローの監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数／.env の自動読み込みと設定管理

設計上、バックテストにおけるルックアヘッドバイアス回避を重視しており、内部処理は対象日を明示的に受け取る形（date 引数）で実装されています。

---

## 主な機能（機能一覧）

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動パース / 読み込み（必要に応じて無効化可能）
  - 環境変数の必須チェック・型変換ユーティリティ

- データ取り込み（kabusys.data）
  - J-Quants クライアント（jquants_client）：認証・ページネーション・レートリミット・リトライ対応
  - ETL パイプライン（pipeline.run_daily_etl 等）：差分取得・保存・品質チェック
  - マーケットカレンダー更新・営業日判定（calendar_management）
  - ニュース収集（news_collector）：RSS 取得・SSRF 対策・前処理・冪等保存
  - データ品質チェック（quality）：欠損、重複、スパイク、日付整合性チェック
  - 監査ログ初期化/管理（audit）: signal/order_request/execution テーブル定義・初期化

- AI / NLP（kabusys.ai）
  - ニュースセンチメント解析（news_nlp.score_news）
  - マクロ + MA200 を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini 等）を JSON mode で呼び出す実装（リトライ・フォールバック有）

- リサーチ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
  - data.stats.zscore_normalize（クロスセクション正規化）

---

## 前提条件 / 必要な依存パッケージ

- Python 3.10+
- pip install で入る代表的パッケージ:
  - duckdb
  - openai
  - defusedxml

（プロジェクトを配布する際は requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone <repo-url>

2. 仮想環境の作成と有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （開発用に追加パッケージがあれば requirements-dev.txt / pyproject.toml を参照してください）

4. 環境変数の準備
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   推奨の .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - OpenAI API を使う機能を利用する場合は OPENAI_API_KEY が必要（もしくは各関数に api_key 引数で渡す）。

5. DuckDB データベース用ディレクトリ作成（必要に応じて）
   - デフォルトの DUCKDB_PATH は data/kabusys.duckdb です。親ディレクトリを作成してください。

---

## 使い方（主要ユースケースの例）

以下は Python API を使った簡単な利用例です。バックテスト／運用用の CLI は実装に応じて別途用意してください。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアを計算して ai_scores テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

- 市場レジーム判定（ma200 + マクロ記事）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可能
```

- ETL の各ジョブを個別に呼ぶ
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
# それぞれ conn, target_date, id_token(optional) を渡す
```

注意:
- OpenAI 呼び出しは API リトライやフォールバックを行いますが、API キーは環境変数 OPENAI_API_KEY または関数引数で渡してください。
- 全ての日付引数は明示的に指定することが推奨されます（内部で date.today() を使わない設計の箇所も多く、ルックアヘッド回避のため）。

---

## 設定と環境変数

- 自動 .env 読み込み:
  - プロジェクトルートの `.env`、さらに `.env.local`（上書き）を自動で読み込みます。
  - テストなどで自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu API 用パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
  - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で利用）
  - DUCKDB_PATH / SQLITE_PATH: データベースファイルパス
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - (その他データ関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research パッケージ（ファクター計算・探索用ユーティリティ）
- (strategy/, execution/, monitoring/ はパッケージ公開対象として __init__ に含まれます。実装はプロジェクト内参照)

各モジュールの役割はファイル冒頭に詳細な docstring（設計方針・処理フロー・戻り値等）が記載されています。まずそれらを参照してください。

---

## テスト・開発時の注意点

- 自動 .env 読み込みを無効にする: テストの際に外部環境に依存させたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- OpenAI/外部 API 呼び出し部分はモックしやすい設計になっています（内部の _call_openai_api を patch して差し替え可能）。
- DuckDB を使ったユニットテストは ":memory:" を使うと便利です。

---

## 追加情報 / 貢献

- バグ報告、機能要望は Issue にてお願いします。
- ライセンス、貢献ガイドライン、テストカバレッジ等はプロジェクトルートの関連ファイル（LICENSE, CONTRIBUTING.md 等）を参照してください（存在する場合）。

---

README は主要な使い方とセットアップをカバーしています。より詳細な API 仕様や実運用の手順（Kabu ステーション連携、Slack 通知フロー、運用監視等）は別途ドキュメント（Design doc / Operation doc）にまとめることを推奨します。