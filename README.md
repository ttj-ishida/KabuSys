# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
価格データの ETL、ニュース収集・NLP、ファクター計算、研究・解析ユーティリティ、監査ログ（トレーサビリティ）、および外部 API クライアント（J‑Quants / OpenAI / kabuステーション）との連携を含みます。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API 失敗時は安全側で継続）」「DuckDB を中心とした軽量なオンディスク DB 利用」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 管理（自動ロード機構、.env.local 上書き）
- J‑Quants API クライアント（価格・財務・カレンダー取得、保存用ユーティリティ）
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- 市場カレンダー管理（営業日判定、next/prev/trading_days、カレンダー更新ジョブ）
- ニュース収集（RSS -> 前処理 -> raw_news に保存する想定のユーティリティ）
- ニュース NLP（OpenAI を用いた銘柄別センチメント集約・ai_scores 書込）
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントを合成）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、Z スコア正規化等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal / order_request / execution のテーブルと初期化関数）
- DuckDB ベースの保存関数（冪等 INSERT / ON CONFLICT の利用）

---

## 必要条件

- Python 3.10 以上（型注釈に `X | Y` を使用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J‑Quants / OpenAI / RSS 配信元 / kabuステーション）

依存関係はプロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください。最低限の例:

pip:
- pip install duckdb openai defusedxml

開発用は仮想環境（venv / poetry / pipenv 等）を推奨します。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>
   - (パッケージが src/ 配置なので PEP 517 準拠のインストール推奨)

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .              # プロジェクトを editable インストール (pyproject がある場合)
   - または `pip install -r requirements.txt` / 必要ライブラリ個別インストール

4. 環境変数 (.env) を作成
   - プロジェクトルートに `.env` または `.env.local` を置けます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - （オプション）KABUSYS_ENV = development | paper_trading | live
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）

   ※ .env のサンプルは .env.example を参照してください（プロジェクトに含められている想定）。

6. DuckDB ファイルの用意
   - デフォルトでは settings.duckdb_path を使用します（例: data/kabusys.duckdb）
   - 監査用 DB を別で作る場合は data.audit.init_audit_db を使えます。

---

## 使い方（代表的なユースケース）

以下は Python スクリプト等から呼び出す例です。ライブラリは DuckDB 接続を引数で受け取る設計が多く、テストしやすくルックアヘッドを防ぐ構成になっています。

1) DuckDB 接続を開く（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None -> 今日（ただしカレンダー調整あり）
print(result.to_dict())
```

3) ニュースセンチメントスコアを生成（OpenAI API 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date はスコア付与日（ニュースウィンドウは前日15:00〜当日08:30 JST）
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```

4) 市場レジーム判定を実行（OpenAI API 必須）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) JPX カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

6) 監査ログ DB の初期化（独立 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は初期化済みの接続
```

7) J‑Quants から直接データ取得（スクリプト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,1))
saved = save_daily_quotes(conn, records)
```

注意:
- score_news / score_regime は OpenAI API 呼び出しを伴います。API 利用に伴うコストとレート制限に注意してください。
- 多くの関数は外部 API で失敗しても例外を上げずフェイルセーフ動作（ログに落とす）する設計です。ただし API キー未設定等の必須エラーは ValueError を投げます。

---

## 環境変数の挙動（自動ロード）

- パッケージロード時（kabusys.config）に自動的にプロジェクトルートを探索して `.env` / `.env.local` を読み込みます。
- 自動ロードを無効化する: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 読み込み優先順位: OS 環境 > .env.local > .env
- .env のパースはシェル風のエスケープ / コメントサポートを備えています。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下にモジュールを置く構成です。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                           # 環境設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースセンチメント集約 / OpenAI 呼び出し
    - regime_detector.py                # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 # J‑Quants API クライアントと DuckDB 保存
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - etl.py                            # ETL 公開型（ETLResult 再エクスポート）
    - calendar_management.py            # 市場カレンダー管理
    - news_collector.py                 # RSS 取得・前処理・保存ユーティリティ
    - quality.py                        # 品質チェック
    - stats.py                          # 統計ユーティリティ（zscore_normalize 等）
    - audit.py                          # 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算
    - feature_exploration.py            # 将来リターン・IC・統計サマリー等
  - research/* (その他の補助関数)
  - ...（戦略・execution・monitoring 等のパッケージプレースホルダ）

※ 実際のファイル構成はリポジトリ全体を参照してください。ここでは主要モジュールを示しています。

---

## 開発 / テスト

- モジュールは単体テスト可能な構成（外部 API 呼び出し箇所は差し替え/モック化しやすい設計）です。
- OpenAI / J‑Quants 呼び出しはそれぞれ内部で専用ラッパー（_call_openai_api / _request）を使っており、ユニットテストではパッチ可能です。
- DuckDB を使ったユニットテストでは ":memory:" を指定してインメモリ DB を利用できます。

---

## 注意事項 / 運用上のヒント

- production（live）での運用時は `KABUSYS_ENV=live` を設定し、ログレベルや Slack 通知などの運用設定を検討してください。
- OpenAI を用いる機能はコストが発生します。バッチ化とレート管理（コード内で実装済み）に留意してください。
- J‑Quants API のレート制限に合わせた RateLimiter とリトライロジックが実装されていますが、運用側でも適切な監視とリトライポリシーを検討してください。
- ニュース収集は外部 RSS に依存するため、SSRF 対策や response サイズ制限など安全性対策を実装しています（news_collector に実装済み）。

---

何か特定の機能の使い方サンプル（ETL のカスタム実行、ai モジュールの詳細なプロンプト制御、監査テーブルの拡張など）が必要であれば、目的に合わせた具体例を追加で作成します。