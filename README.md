# KabuSys

日本株向けのデータ基盤・リサーチ・AI支援を備えた自動売買（運用支援）ライブラリです。  
DuckDB を中心とするローカルデータレイヤ、J-Quants API 経由の ETL、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの差分取得（株価日足 / 財務 / マーケットカレンダー）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL パイプライン（run_daily_etl）

- ニュース収集・NLP
  - RSS ベースのニュース収集（SSRF対策・サイズ制限・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（score_news）
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（score_regime）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化ユーティリティ

- 監査・オーディット
  - シグナル → 発注 → 約定までの監査テーブル定義＆初期化
  - 冪等キー（order_request_id / broker_execution_id）を考慮したトレーサビリティ設計

- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数は Settings クラスで型チェックとバリデーション

---

## セットアップ手順

前提: Python 3.10 以上、Git がインストールされていることを想定しています。

1. リポジトリをクローン（任意）
   - git clone <リポジトリ URL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - このリポジトリに requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主要な依存例:
     - duckdb
     - openai
     - defusedxml
     - （必要に応じて他の HTTP / DB 補助ライブラリ）

   注: パッケージ配布形態によっては `pip install -e .` 等を使います。

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` を作成してください。
   - 重要な環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN  ← J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD       ← kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL       ← （任意、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN         ← Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID        ← Slack チャネルID（必須）
     - DUCKDB_PATH             ← DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH             ← SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV             ← development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL               ← DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - OPENAI_API_KEY          ← OpenAI の API キー（AI モジュール呼び出し時に使用）

   - 自動読み込みの制御:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化します（テスト時などに便利）。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB データベース初期化（必要に応じて）
   - データベースはコード実行時に自動でファイルを作成できますが、監査DBを別途初期化するユーティリティもあります（下記参照）。

---

## 使い方（基本例）

以下はライブラリの主要な使い方の例です。実際にはログ設定や例外処理を組み込んでください。

- 日次 ETL の実行（株価/財務/カレンダーの差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースの AI スコアリング（指定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数が返る
print("書き込んだ銘柄数:", written)
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

- ファクター計算（モメンタム等）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
print(factors[:5])
```

注意点:
- AI（OpenAI）呼び出しを行う関数は、引数で API キーを渡すことが可能です（テスト容易性のため）。
- 各モジュールは Look-ahead bias を避けるように設計されています（内部で date.today() を直接参照しない等）。
- DuckDB のバージョンや接続設定に注意してください（executemany の空リスト扱い等で互換性確保済みですが、環境依存の差異が出る可能性があります）。

---

## 設定（Settings）— 環境変数一覧

Settings クラスで参照される主な環境変数（必須 / 任意）:

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 任意（デフォルトあり）:
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development / paper_trading / live) — default: development
  - LOG_LEVEL (DEBUG/INFO/... ) — default: INFO
  - OPENAI_API_KEY（AI 呼び出し時に環境変数として使用可能）

.env 自動読み込み:
- OS 環境変数 > .env.local > .env の優先順位で読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構成（概略）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント（銘柄別）
    - regime_detector.py    — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETL の公開型（ETLResult）
    - calendar_management.py— 市場カレンダー管理 / 営業日判定
    - news_collector.py     — RSS ニュース収集
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー

各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数として受け取る設計が多く、テストや運用で接続を差し替えて利用できます。

---

## 開発・テストに関する補足

- テスト用の環境を簡単に作るには、DuckDB のインメモリ接続(":memory:") を使うと便利です。
- AI API 呼び出し部分は内部で分離されており、テスト時は各モジュールの _call_openai_api 等をモックしてレスポンスを差し替えられるようになっています。
- 外部 API 呼び出し（J-Quants / OpenAI / RSS）にはレート制御やリトライが備わっていますが、本番運用では適切なキー管理・ログ監視を行ってください。

---

もし README に追加したい具体的な実行例（cron での定期実行、Docker 化、CI 設定、.env.example のテンプレート等）があれば、用途に合わせたサンプルを追記します。必要なら .env.example のテンプレートも作成します。