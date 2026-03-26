# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ収集）、ニュース NLP（OpenAI を利用した銘柄センチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などの機能を提供します。

主な設計方針は「ルックアヘッドバイアスを防ぐ」「DuckDB/ローカル DB に対する冪等保存」「外部 API の失敗に対するフェイルセーフ」です。

バージョン: 0.1.0

---

## 機能一覧

- data
  - ETL パイプライン（prices / financials / market calendar の差分取得・保存）
  - J-Quants API クライアント（トークン取得、自動リトライ、レート制御、ページネーション）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar 更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF / Gzip / トラッキング除去対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal / order_request / executions テーブルの初期化・管理）
  - 統計ユーティリティ（Z スコア正規化等）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメント評価）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク変換）
- config
  - 環境変数読み込み（.env / .env.local の自動読み込み、プロジェクトルート検出）
  - settings オブジェクト経由の設定取得

---

## 要求環境 / 依存

以下は主な依存パッケージ（プロジェクトの pyproject.toml / requirements.txt を参照してください）:

- Python 3.10+
- duckdb
- openai (OpenAI Python client)
- defusedxml
- その他: typing, urllib, logging 等の標準ライブラリ

開発環境でのセットアップ例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 開発中でパッケージ情報が pyproject.toml にある場合:
pip install -e .
# 最低限の依存を直接入れる場合:
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env の設定

プロジェクトはルートにある `.env` / `.env.local` を自動で読み込みます（ルート判定は .git または pyproject.toml を基準）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数（config.Settings に対応）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略時 data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（省略時 development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（要点）

1. リポジトリ取得
   - git clone ...
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存インストール
   - pip install -e . もしくは pip install duckdb openai defusedxml
4. 環境変数設定
   - ルートに `.env` を作成（上記参照）
5. DuckDB / 監査 DB 初期化（必要に応じて）
   - Python REPL で実行例（下記参照）

---

## 使い方（Python API 例）

以下は代表的な利用例です。実行はプロジェクト配下の Python 環境で行ってください。

- DuckDB 接続作成:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー、株価、財務の差分取得・品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai_score）を計算して ai_scores に書き込む:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"written: {written} codes")
```

- 市場レジーム判定:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_kabusys.duckdb")
# audit_conn は初期化済みの duckdb 接続
```

- ファクター / リサーチ関数の利用:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- カレンダー関連ユーティリティ:

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- AI / OpenAI 呼び出しはコストがかかります。テスト時は該当関数内の API 呼び出しヘルパーをモックできます（news_nlp._call_openai_api, regime_detector._call_openai_api 等）。
- データベース書き込みは冪等化を考慮しており、部分失敗時でも既存データを保護する実装になっています。

---

## 自動読み込みの挙動について

- kabusys.config はパッケージロード時にプロジェクトルート（.git または pyproject.toml）を探し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先されます）。
- 自動ロードを無効化するには、プロセス起動前に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- settings オブジェクトはプロパティアクセスで必須項目の未設定を検出して ValueError を投げます。

---

## ディレクトリ構成

リポジトリの主要ファイル／モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                             : 環境変数 / 設定読み取り
  - ai/
    - __init__.py                          : news_nlp.score_news, regime_detector.score_regime
    - news_nlp.py                          : ニュースセンチメント生成（OpenAI）
    - regime_detector.py                   : 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py               : 市場カレンダー管理
    - etl.py / pipeline.py                 : ETL パイプライン
    - jquants_client.py                    : J-Quants API クライアント（取得・保存）
    - news_collector.py                    : RSS 収集・正規化
    - quality.py                           : データ品質チェック
    - stats.py                             : 統計ユーティリティ（zscore 等）
    - audit.py                             : 監査ログ DDL / 初期化
    - pipeline.py                          : ETL のエントリポイント + ETLResult
    - etl.py                               : (公開インタフェースの再エクスポート)
  - research/
    - __init__.py
    - factor_research.py                   : モメンタム / ボラティリティ / バリュー
    - feature_exploration.py               : 将来リターン、IC、summary、rank
  - research/（その他ユーティリティ群）

この README に記載の API は主要なものの概要であり、各モジュール内に詳細な docstring と設計方針が含まれています。用途に応じて該当モジュールの docstring を参照してください。

---

## テスト / 開発上の注意

- OpenAI / J-Quants / 外部ネットワーク呼び出しはモックしてユニットテストを作成してください。news_nlp, regime_detector, jquants_client, news_collector にはテストしやすい差し替えポイントが用意されています（内部の _call_openai_api、_urlopen など）。
- DuckDB に対する executemany の空リスト渡しに注意（実装内でチェック済み）。
- 本リポジトリ単体では「発注実行（ブローカーへの送信）」機能は含まれていません。監査ログ用スキーマは提供されますが、実際のブローカー連携は別実装／ラッパーが必要です。
- 本番環境（KABUSYS_ENV=live）での利用は十分なテストと運用設計後に行ってください。

---

何か追加したいサンプルや、README に含める具体的なコマンド（CI, デプロイ手順など）があれば教えてください。必要に応じてサンプル .env.example や Dockerfile、簡易 CLI の追加案も作成できます。