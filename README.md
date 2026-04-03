# KabuSys

日本株向けの自動売買 / データ基盤ライブラリセットです。  
ETL、ニュース収集 / NLP、ファクター計算、監査ログ、J-Quants クライアント、レジーム判定など、運用に必要な主要機能をモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の要件に基づいて設計されています。

- DuckDB をデータレイク／ワークスペースとして利用する ETL パイプライン
- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークンリフレッシュ対応）
- RSS によるニュース収集と SSRF 対策・入力正規化
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / マクロセンチメント計算（JSON Mode）
- ファクター計算（モメンタム/バリュー/ボラティリティ等）と研究用ユーティリティ
- 監査（監査ログ）スキーマの初期化と管理（注文から約定までのトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針として、バックテスト等でのルックアヘッドバイアスを避ける実装（日時参照の制御）や、外部 API 呼び出しのフォールバック・堅牢性を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数・.env の自動読み込み（プロジェクトルート検出）と設定ラッパー
  - 必須設定の検証

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / ページネーション / レート制御）
  - pipeline / etl: 日次 ETL（prices / financials / calendar）の差分取得・保存・品質チェック
  - news_collector: RSS 収集、前処理、冪等保存、SSRF 対策
  - calendar_management: JPX カレンダー管理 / 営業日判定 / 夜間更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
  - stats: z-score 正規化など汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュース記事を銘柄毎に集約して OpenAI でセンチメントを算出・ai_scores へ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して市場レジーム判定

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリューの計算関数
  - feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリ、ランク変換 等

---

## セットアップ手順

動作要件（推奨）
- Python 3.10 以上（3.11 推奨）
- DuckDB
- OpenAI SDK（openai）
- defusedxml（RSS パーサ保護）
- （任意）その他標準ライブラリに依存

基本的なインストール例:

1. 仮想環境を作成 & 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config がルートを検出）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（または利用推奨）環境変数例（.env）:

- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...           （ai モジュールを使う場合）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易ガイド）

以下は代表的なユースケースの Python スニペットです。各関数は duckdb の接続オブジェクト（DuckDBPyConnection）を受け取ります。

共通セットアップ（例）:
```python
from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が使われます
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースのセンチメントスコア計算（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用
written_count = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {written_count} codes")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 19))
```

4) 監査ログ DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って監査テーブルへアクセス
```

5) カレンダー・営業日ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

6) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

records = calc_momentum(conn, date(2026, 3, 19))
# records は dict のリストで返る
```

注意点:
- ai モジュールは OpenAI の JSON Mode を利用する設計（response_format={"type": "json_object"}）。API バージョン・SDK の互換性に注意してください。
- 外部 API が失敗した場合、フォールバックや部分成功で継続する設計になっています（例: LLM の失敗時はスコアを 0 にフォールバックなど）。
- DuckDB の executemany に空リストを渡すと失敗するバージョン依存の挙動に配慮しています（コード中でチェック済み）。

---

## ディレクトリ構成

主要なソースファイル構成（src/kabusys 以下）:

- src/kabusys/__init__.py
- src/kabusys/config.py

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py

- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

- src/kabusys/data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 data 関連ユーティリティ)

各モジュールの役割は上の「機能一覧」を参照してください。

---

## 環境変数／設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) - J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) - kabu ステーション API 用パスワード
- OPENAI_API_KEY (ai 機能を使う場合) - OpenAI API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知等で使用)
- DUCKDB_PATH / SQLITE_PATH - DB ファイルパス
- KABUSYS_ENV - environment: development / paper_trading / live
- LOG_LEVEL - DEBUG/INFO/WARNING/ERROR/CRITICAL

自動読み込みの順序: OS 環境変数 > .env.local > .env  
自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 開発者向けメモ

- DuckDB のバージョンによっては executemany や list パラメータバインドの挙動が異なるため、コード中で互換性対策が施されています。
- OpenAI API 呼び出しはリトライ・バックオフ・エラー分類を行い、API の一時エラーでは例外を投げずフォールバックする箇所があります（堅牢性重視）。
- テストを行う際、外部 API 呼び出し箇所はモックしやすいよう設計されています（内部の _call_openai_api などをパッチする）。
- ログレベルや環境（paper_trading / live）に応じた挙動切替を行うため、KABUSYS_ENV を正しく設定してください。

---

## ライセンス / 貢献

（本リポジトリのライセンス情報があればここに記載してください）

---

この README はコード内の docstring / コメントを基に作成しています。より詳細な操作手順や運用の流れ（デプロイ・監視・バックテスト連携等）は別途ドキュメント化することを推奨します。必要であれば、サンプルの .env.example や簡易の CLI スクリプト例も追加できます。必要な場合は教えてください。