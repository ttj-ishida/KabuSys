# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株のデータ取得・ETL、ニュース NLP（LLM）による銘柄センチメント評価、市場レジーム判定、監査ログ（トレーサビリティ）やリサーチ用ファクター計算等を提供する Python モジュール群です。本 README はローカル開発／実行のための概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## 概要

このコードベースは次の主要な関心領域を分離して実装しています。

- データ収集・ETL（J-Quants API 経由、DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）とニュース NLP（OpenAI を用いた銘柄センチメント）
- 市場レジーム判定（ETF の 200 日 MA とマクロニュースの組合せ）
- リサーチ用ファクター（モメンタム、ボラティリティ、バリュー等）
- 発注・約定の監査ログスキーマ（監査テーブルの初期化ユーティリティ）
- 設定管理（環境変数 / .env 自動読み込み）

設計方針として、バックテストでのルックアヘッドバイアス回避、冪等性（DB 保存時の ON CONFLICT/UPDATE）、外部 API の堅牢なリトライ・レートリミット制御を重視しています。

---

## 主な機能一覧

- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
  - 株価（raw_prices）、財務（raw_financials）、市場カレンダー（market_calendar）の差分取得と保存
  - 品質チェック（kabusys.data.quality.run_all_checks）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ページネーション対応、トークン自動リフレッシュ、レート制限、リトライ
  - save_* 関数は DuckDB に対して冪等保存を行う
- ニュース収集（kabusys.data.news_collector.fetch_rss）
  - RSS 正規化、SSRF 防御、トラッキングパラメータ除去、前処理
- ニュース NLP（kabusys.ai.news_nlp.score_news）
  - gpt-4o-mini を利用した銘柄ごとのセンチメント評価、結果は ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して regime を判定
- リサーチ機能（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、forward returns、IC 計算、統計サマリー
- 監査ログ初期化（kabusys.data.audit.init_audit_db / init_audit_schema）
  - signal_events / order_requests / executions とインデックスの作成

---

## 要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK: OpenAI クライアントを使う新仕様)
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

（実環境に合わせて requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境作成（例）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # もしくはプロジェクトの requirements.txt / pyproject.toml を使用
   ```

4. 環境変数を設定（.env をプロジェクトルートに配置可能）
   - 自動的に読み込まれる優先順位: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須（少なくともテスト・実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を実行する場合）
   - 任意:
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH / SQLITE_PATH（デフォルトは data/kabusys.duckdb / data/monitoring.db）

5. DuckDB データベース用ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## .env 例 (.env.example)

例（プロジェクトルートに `.env` を作成）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

（注意: 実鍵はリポジトリにコミットしないでください）

---

## 使い方（代表的な例）

以下は Python スクリプト / REPL から呼ぶ例です。

1. DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニュース NLP（指定日）のスコアリング（ai_scores テーブルに書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数
print("written:", written)
```

4. 市場レジーム判定（regime を market_regime テーブルへ書き込む）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5. 監査ログ DB の初期化（監査専用 DB を別ファイルに作成する例）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path
conn_audit = init_audit_db(Path("data/audit.duckdb"))
# conn_audit に対して audit テーブルが作成されます
```

6. カレンダー更新ジョブ（J-Quants から市場カレンダーをフェッチして保存）
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date
calendar_update_job(conn, lookahead_days=90)
```

メソッドの多くは例外を投げる場合があります（API エラーや必須環境変数未設定など）。ログレベルは環境変数 LOG_LEVEL で調整してください。

---

## 開発・テストのヒント

- OpenAI / ネットワーク呼び出しはテストでモック可能です。モジュール内の _call_openai_api 等を patch してレスポンスを模擬できます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")
- 環境変数の自動ロードを無効化してユニットテストを制御する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB の接続はインメモリ ":memory:" を使えます（テスト高速化に便利）:
  ```python
  conn = duckdb.connect(":memory:")
  ```
- news_collector はネットワーク・XML の安全性に配慮（SSRF 検査、defusedxml、サイズ制限）しています。実際の RSS フィードで動作確認する際はログを確認してください。

---

## ディレクトリ構成（主要ファイル）

（ソースは `src/kabusys` 下に配置されています。主要モジュールを抜粋）

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
    - quality.py
    - calendar_management.py
    - stats.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - researchパッケージでは zscore_normalize 等も利用
- data/ (推奨、データベースファイル等を格納)
  - kabusys.duckdb (デフォルト)
  - monitoring.db (SQLite 用)
- .env / .env.local (環境変数)

---

## 環境変数の主要項目（まとめ）

- 必須（機能により必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールを実行する場合）
  - KABU_API_PASSWORD — kabu API パスワード（発注を行う場合）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を行う場合
- オプション
  - KABUSYS_ENV — development / paper_trading / live（既定: development）
  - LOG_LEVEL — ログレベル（既定: INFO）
  - DUCKDB_PATH — DuckDB DB ファイルパス（既定: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視用）パス（既定: data/monitoring.db）
- 自動ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化

---

## 注意点・設計上の留意事項

- ルックアヘッドバイアスを避けるため、多くの処理は `target_date` を明示して実行する設計になっています。内部で date.today() を参照しないことが原則です（例外は明示された箇所のみ）。
- DuckDB の executemany は空リストが渡せないバージョンの挙動を考慮しているので、保存処理は空チェックを行っています。
- OpenAI / J-Quants 呼び出しはリトライと指数バックオフを備えています。API キーやネットワークの状態による失敗はフェイルセーフとしてゼロスコアやスキップで処理継続する箇所が多くあります。
- 機密情報（トークン等）は .env ではなく、CI や本番ではシークレット管理システムの利用を推奨します。

---

もし README に追加したい情報（CLI 実行例、Docker 化、GitHub Actions の設定例、詳細なテーブルスキーマなど）があれば教えてください。必要に応じてサンプルスクリプトや初期データロード手順も作成します。