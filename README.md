# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
J-Quants / RSS / OpenAI を取り込み、ETL、データ品質チェック、ニュースNLP、レジーム判定、リサーチ用ファクター計算、監査ログ（注文 → 約定のトレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を参照しない処理が多い）
- 冪等性（DB への保存は ON CONFLICT 等で保護）
- API 呼び出しはリトライ・バックオフ・レート制限を備える
- セキュリティ対策（RSS の SSRF 防止、XML の defusedxml 利用など）

---

## 機能一覧

- データ取得／ETL
  - J-Quants 経由の株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得（pagination 対応、トークン自動リフレッシュ、レート制御、リトライ）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク（急騰・急落）検出、重複チェック、日付整合性チェック
- ニュース収集／NLP
  - RSS からニュースを収集し raw_news に保存（URL 正規化、トラッキング除去、SSRF 対策、gzip 対応）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント計算（ai_scores へ保存）
- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離と、マクロニュースの LLM センチメントを合成して日次で 'bull' / 'neutral' / 'bear' を判定
- リサーチ用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化
  - UUID ベースのトレーサビリティ（order_request_id を冪等キーとして二重発注防止）
- 設定管理
  - .env（/ .env.local）自動読み込み（プロジェクトルート検出）、環境変数アクセスラッパー（kabusys.config.settings）

---

## 要件（主な依存）

- Python 3.10+
- パッケージ
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ：urllib, logging, json, datetime など）

必要に応じて他のライブラリが追加される場合があります（プロジェクトの packaging に従ってください）。

---

## インストール（開発環境向け）

1. Python 3.10 以上を準備
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトを editable インストールする場合）
     - pip install -e .

※ 実際のプロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください。

---

## 環境変数（.env の例）

このプロジェクトは .env / .env.local を自動ロードします（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の代表的な環境変数（使用する機能により変わります）：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル
- OPENAI_API_KEY: OpenAI クライアントで使用（score_news / score_regime 実行時に必須）

オプション（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
```

注意:
- .env.local は .env を上書きします（OS 環境変数は上書きされない）。
- config.Settings を通じて settings.jquants_refresh_token 等でアクセスできます。

---

## クイックスタート（コード例）

以下はライブラリの主要な使い方の例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を開いて ETL を実行する（日次ETL）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを作成する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => env OPENAI_API_KEY を使用
print(f"wrote {written} ai_scores")
```

- 市場レジームを判定して書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # settings.duckdb_path は Path を返す
```

- 設定値を見る:
```python
from kabusys.config import settings
print(settings.kabu_api_base_url)
print(settings.is_live)
```

---

## 主要なディレクトリ構成（src/kabusys）

（抜粋 — 実際のリポジトリは他ファイルがあるかもしれません）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS のニュースをまとめて OpenAI に投げ、ai_scores を生成
    - regime_detector.py
      - ETF の MA200 とマクロニュースセンチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API との HTTP クライアント（レート制御、トークン管理、保存関数）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult を公開
    - calendar_management.py
      - market_calendar を扱うヘルパー（is_trading_day, next_trading_day 等）
    - news_collector.py
      - RSS 収集・前処理・raw_news 保存
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - 汎用統計（zscore_normalize など）
    - audit.py
      - 監査ログテーブル定義と初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・バリュー・ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー等
  - ai、data、research 以下はそれぞれの責務に分離され、外部サーバ（取引所 API・OpenAI 等）へのコールはモジュール化されています。

---

## 設計上の注意点 / 運用上のヒント

- OpenAI 呼び出しや外部 API は課金・レート制限の対象です。開発環境での実行は注意してください。テストでは _call_openai_api をモックして実行できます（モジュール内で差し替え可能に設計）。
- データベースへの保存は冪等（ON CONFLICT）を意識していますが、運用時はバックアップを取ってください。
- ETL は部分失敗を許容し、品質チェックは結果を返す形式です（呼び出し側で警告／停止を判断）。
- .env/環境変数の管理は慎重に。機密情報（トークン等）は安全なシークレット管理を推奨します。
- news_collector は外部 URL にアクセスするため、企業セキュリティポリシーと合致することを確認してください（SSRF 対策は組み込まれていますが、公開環境でのリスクは別途評価が必要です）。

---

## 貢献 / ライセンス

この README はコードから抽出した設計意図と使い方の概要を示します。実際の貢献方法やライセンス情報はリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば README にサンプル .env.example や requirements.txt、より詳しい API 使用例（関数引数の詳細や戻り値例）を追加します。どの部分を詳述しますか？