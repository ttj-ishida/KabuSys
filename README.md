# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
データETL、ニュース収集・NLP（OpenAI）、ファクター・リサーチ、監査ログ（トレーサビリティ）、市場カレンダー管理など、量的運用に必要な基盤機能群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「堅牢なエラーハンドリング」「テスト容易性」です。

---

## 機能一覧

- 設定管理
  - `.env` / 環境変数の自動ロード（プロジェクトルート判定）
  - `kabusys.config.settings` による型付きアクセス

- データプラットフォーム（DuckDB ベース）
  - J-Quants API クライアント（取得・保存・ページネーション対応・リトライ/レート制御）
  - 日次 ETL パイプライン（株価 / 財務 / カレンダー取得 + 品質チェック）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
  - マーケットカレンダー管理（JPX カレンダー取得・営業日判定関数）
  - ニュース収集（RSS → raw_news、SSRF / XML 攻撃対策、トラッキング除去）
  - 監査ログスキーマ初期化（signal / order_request / executions）

- AI（OpenAI）を用いた解析
  - ニュースセンチメントスコアリング（銘柄ごとに ai_scores へ保存）: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメント合成）: `kabusys.ai.regime_detector.score_regime`
  - 両モジュールは JSON Mode（gpt-4o-mini 等）での呼び出しと堅牢なリトライ処理を備える

- リサーチ (研究用)
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化

- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - ETL 結果データクラス `ETLResult`
  - DuckDB 初期化・監査DB初期化ユーティリティ

---

## 要件

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに pyproject/requirements がある想定です。上記は主要依存を列挙しています）

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへコピー

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトの要件ファイルがあればそれを利用してください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として必要なキーを配置します。自動ロードはデフォルトで有効です（`.env.local` は優先して上書きされます）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等を行う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出すサンプルです。

- 設定の参照
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# conn を各関数に渡して利用する
```

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- News NLP スコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {n_written} symbols")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.duckdb")
# 以後 conn を監査ログ用に使用
```

- カレンダー/営業日ヘルパー
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- AI を使う関数は API キー解決を引数（api_key）か環境変数 `OPENAI_API_KEY` から行います。キー未設定時は ValueError を投げます。
- 多くの書き込みは冪等的に設計されています（ON CONFLICT / DELETE→INSERT パターンなど）。
- テスト時は内部の API 呼び出し（例: `_call_openai_api`）をモックして制御可能です。

---

## ディレクトリ構成（主なファイルと簡単な説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（アプリ設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約し OpenAI でスコアリング、ai_scores へ保存
    - regime_detector.py
      - ETF(1321)のMA200乖離 + マクロニュースのLLMセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - etl.py
      - ETLResult の公開
    - pipeline.py
      - 日次 ETL 実行（価格・財務・カレンダー取得 + 品質チェック）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログ（signal / order_requests / executions）の DDL / 初期化
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・トークン管理・レート制御）
    - news_collector.py
      - RSS 収集・前処理・raw_news 保存（SSRF/サイズ/XML対策実装）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー 等の計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー・ランク関数
  - (ほか、strategy/execution/monitoring など公開を意図したパッケージ名が __all__ に記載されていますが、上記が主要な実装ファイル群です)

---

## テスト / 開発メモ

- 環境変数自動読み込み:
  - プロジェクトルートは __file__ の親階層を上に辿って `.git` または `pyproject.toml` の有無で判定します。
  - `.env` → `.env.local` の順で読み込み（.env.local は上書き）。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- OpenAI 呼び出し:
  - `_call_openai_api` はテスト時に unittest.mock.patch で置き換えて制御可能です（news_nlp と regime_detector で別実装になっている点に注意）。

- DuckDB について:
  - 初回はテーブル作成ロジック（別モジュールにある想定）でスキーマを作成してから ETL を実行してください。
  - `init_audit_db` は監査用の DB を初期化して接続を返します。

---

## トラブルシューティング

- 環境変数が見つからないエラー:
  - settings の必須プロパティは `_require` により未設定時に `ValueError` を投げます。`.env.example` を参考に `.env` を作成してください。
  - 自動ロードを無効化している場合は明示的に環境変数をエクスポートしてください。

- OpenAI / J-Quants API エラー:
  - ネットワークやレート制限に対してリトライロジックが組まれていますが、長時間の失敗やキー失効は上位で対処してください。
  - J-Quants のトークンは `JQUANTS_REFRESH_TOKEN` を使って自動リフレッシュされます。

---

README はここまでです。必要であれば、運用上のワークフロー（cron による nightly ETL、Slack 通知の統合、監査ログの参照クエリ例、CI 用の設定）や `.env.example` のテンプレートも追加できます。どの情報を優先的に追加しますか？