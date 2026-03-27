# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ニュースNLP（OpenAI）→ リサーチ（ファクター計算）→ 売買監査ログ管理 といったワークフローを想定して設計されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを提供します。

- data: J-Quants API クライアント、ETL パイプライン、ニュース収集、マーケットカレンダー、データ品質チェック、監査ログ初期化などのデータ基盤機能
- ai: ニュースのセンチメント分析（OpenAI）や市場レジーム判定
- research: ファクター計算・特徴量探索・統計ユーティリティ
- config: 環境変数／設定の読み込み・管理

設計方針の一部：
- Look-ahead バイアス対策（target_date に依存し datetime.today() を直接参照しない実装）
- DuckDB を中心としたローカル分析データベース
- 冪等性（ETL / DB 書き込みは ON CONFLICT / idempotent）
- 外部 API 呼び出しに対するリトライやフェイルセーフ（API失敗時はスキップやデフォルト値で継続）

---

## 主な機能一覧

- J-Quants API クライアント（株価・財務・カレンダー・上場銘柄情報）
  - レートリミット管理、トークン自動リフレッシュ、ページネーション対応
- ETL パイプライン（data.pipeline）
  - 差分取得、バックフィル、品質チェックの統合（run_daily_etl）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付整合性チェック
- ニュース収集（data.news_collector）
  - RSS 収集、SSRF 対策、トラッキングパラメータ除去、記事ID生成、前処理
- ニュースNLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント集計（batch）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアの重み合成
- リサーチ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算、Z-score 正規化
- 監査ログ（data.audit）
  - シグナル→発注→約定をトレースするテーブル群と初期化ユーティリティ

---

## 必要条件 / 依存パッケージ（主なもの）

- Python 3.10+
- duckdb
- openai (OpenAI の公式 SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging 等）

pip 等でインストールして使ってください（パッケージ化されている前提での例）:

```
pip install duckdb openai defusedxml
```

（プロジェクトをパッケージとして配布する場合は setup/pyproject に依存関係を記載してください）

---

## 環境変数 / 設定

KabuSys は .env ファイルまたは環境変数から設定を読み込みます。読み込み優先順位は次の通りです：

1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings クラスで使用）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API 用パスワード（利用する場合）
- KABU_API_BASE_URL（任意）: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID（必須）: Slack 通知先チャネル ID
- OPENAI_API_KEY（必須 for AI functions）: OpenAI API 呼び出しに使うキー（各関数呼び出しで引数として渡すことも可）
- DUCKDB_PATH（任意）: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意）: 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL（任意）: ログレベル ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

注意: Settings プロパティは未設定の必須環境変数について ValueError を送出します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを取得
2. 仮想環境作成・有効化（推奨）
3. 依存パッケージをインストール（duckdb, openai, defusedxml 等）
4. プロジェクトルートに `.env`（および任意で `.env.local`）を作成し必須環境変数を設定
   - .env.example を参考に作成してください（リポジトリに同梱されている想定）
5. DuckDB データベース（デフォルト data/kabusys.duckdb）を用意（init スクリプトがあれば実行）
6. 必要に応じて audit DB を初期化

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
```

---

## 使い方（抜粋・例）

以下はライブラリ API を直接呼ぶ想定のサンプルです。実運用では CLI やジョブスケジューラから呼び出します。

- DuckDB 接続を作って daily ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai スコア）を実行する:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定済みか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print("written:", n_written)
```

- 市場レジーム判定を実行する:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用の DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb_file.duckdb")
# conn を使って以降の監査テーブル利用や CRUD を行う
```

- 市場カレンダー周りのユーティリティ例:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注記:
- OpenAI 呼び出しはネットワークエラーやレート制限を考慮してリトライ実装がありますが、APIキー未設定時は ValueError を投げます。
- テスト時には内部の _call_openai_api をモックして API 呼び出しを差し替えられる設計です。

---

## よくあるトラブルシューティング

- 設定エラー（ValueError: 環境変数が設定されていません）
  - 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY）を確認してください。
- DuckDB にテーブルがない / schema エラー
  - ETL 実行前にスキーマ初期化処理を実行するか、必要なテーブルが存在することを確認してください（ETL 実装は既存テーブルへ upsert を行う想定）。
- OpenAI のレート制限 / 429
  - SDK 側と本ライブラリ側でリトライを行いますが、過度な呼び出しは避け、適切にバッチサイズ等を調整してください。

---

## ディレクトリ構成

主要ファイル・モジュールの概略ツリー（src/kabusys 以下）:

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
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記は本リポジトリの主要なモジュール構成を示しています。各モジュール内にさらに細かい関数や補助ユーティリティがあります。）

---

## 開発メモ / 設計上の注意点

- 多くの関数は Look-ahead バイアスを避けるために target_date を明示的に受け取る実装です。バックテストや再現性を保つため、この方針に従ってください。
- OpenAI とのやり取りは JSON Mode（厳密な JSON 出力）を想定しており、レスポンスパースの堅牢化（前後テキストの切り出し等）を行っています。テストでは _call_openai_api をモックしてください。
- RSS 取得は SSRF 対策や Gzip / サイズ上限（10MB）などの安全策を実装しています。
- DuckDB に対する大量の executemany を行う際は、空リストを渡さない安全チェック（DuckDB 0.10 の制約）などの配慮があります。

---

もし README に追加したい情報（例: CLI コマンド、CI 設定、より詳細なスキーマ定義、.env.example 例など）があれば教えてください。必要に応じて追記します。