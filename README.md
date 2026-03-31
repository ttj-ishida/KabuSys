# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、データ収集（ETL）、品質チェック、ニュース NLP、ファクター計算、マーケットレジーム判定、監査ログといった一連の機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要求環境（Prerequisites）
- セットアップ手順
- 簡単な使い方（例）
- 環境変数一覧（.env 例）
- ディレクトリ構成
- 補足・注意事項

---

プロジェクト概要
----------------
KabuSys は日本株のデータプラットフォームと解析・監査・ETL機能を備えたライブラリ群です。DuckDB をデータストアに用い、J-Quants API から株価・財務・カレンダーを取得、RSS ニュース収集→AI（OpenAI）でニュースセンチメントを算出、ファクター計算やレジーム判定、発注監査テーブルの初期化などバックオフィス / 研究用途に向けた機能を提供します。

設計方針（抜粋）
- ルックアヘッドバイアスの排除（target_date を明示し内部で date.today() を直接参照しない）
- DuckDB を使った効率的な SQL+Python 実装
- 冪等性を重視（ETL 保存は ON CONFLICT / DO UPDATE）
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える

---

機能一覧
--------
主な機能（モジュール別）
- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数からの設定取得（J-Quants トークン、kabu API パスワード、Slack 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証、ページネーション、保存用ユーティリティ）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - calendar_management: 市場カレンダー管理（営業日判定 / next/prev/get）
  - audit: 監査ログスキーマ初期化（signal_events, order_requests, executions 等）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores へ保存）
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュース（LLM）を組合せた市場レジーム判定
- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティなどのファクター計算（calc_momentum, calc_value, calc_volatility）
  - feature_exploration: 将来リターン、IC、統計サマリー等

その他
- DuckDB 用の監査 DB 初期化ユーティリティ（init_audit_db / init_audit_schema）
- ETL 実行結果を表現する ETLResult データクラス

---

要求環境（Prerequisites）
-----------------------
- Python >= 3.10
- 推奨パッケージ（最低限）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime 等

（実行環境によっては追加の依存がある可能性があります。setup.py / pyproject.toml があればそちらを参照してください。）

---

セットアップ手順
----------------

1. リポジトリをクローン（省略可）
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。）
   開発インストール（パッケージ化されている場合）:
   pip install -e .

4. .env を準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env を置くと、自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベース等の初期フォルダを用意する（必要に応じて）
   デフォルトでは data/kabusys.duckdb、data/monitoring.db、data/execution.pid 等を使用します。settings.duckdb_path で変更できます。

---

環境変数（主要なもの）
---------------------
必須（Settings._require を用いて必須チェックされるもの）
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD      — kabuステーション API のパスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack チャンネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL      — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視用）データベースパス（デフォルト data/monitoring.db）
- PID_FILE_PATH          — 実行 PID ファイル（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV            — environment: development | paper_trading | live（デフォルト development）
- LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY         — OpenAI API キー（ai.score_news, regime_detector で使用）

.env 例
```
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env.local がある場合、.env.local は .env の上書き（優先）で読み込まれます。OS 環境変数は最優先で保護されます。

---

簡単な使い方（コード例）
----------------------

事前準備: DuckDB 接続と settings
```python
import duckdb
from kabusys.config import settings

# DuckDB 接続（ファイルまたは :memory:）
conn = duckdb.connect(str(settings.duckdb_path))
```

ETL の日次実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# 当日を対象に ETL 実行（ターゲット日を明示）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

ニュース NLP スコア付け（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは env OPENAI_API_KEY を設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

市場レジーム判定（ETF 1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# api_key は省略すると環境変数 OPENAI_API_KEY を参照
score_regime(conn, target_date=date(2026, 3, 20))
```

監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルを指定
```

ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

ディレクトリ構成（抜粋）
-----------------------
以下は本コードベースに含まれる主要モジュールとファイルのツリー（src/kabusys 以下）。実際のリポジトリでは README に記載の他ファイルがある場合があります。

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
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他の研究補助モジュール）
  - (その他: monitoring, strategy, execution を __init__ で公開する設計あり)

---

補足・注意事項
--------------
- OpenAI API を使用する処理（news_nlp, regime_detector）は API 呼び出し制限とコストに注意してください。失敗した場合はフェイルセーフ（スコア 0.0 等）で継続する設計ですが、必要に応じてリトライ設定やログを確認してください。
- J-Quants API 呼び出しはレート制御・リトライ・トークンリフレッシュを内蔵しています。
- DuckDB の executemany 等はバージョン依存の注意事項がコード内にあるため、利用する DuckDB のバージョンに応じた動作確認を行ってください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 危険なネットワークリクエスト（news_collector）は SSRF 対策や受信上限を設けていますが、実運用では追加のガード（プロキシ、ホワイトリスト）を検討してください。
- 本 README はコードの現状（提供されたファイル群）に基づく概要です。実運用ではログ設定、例外監視、CI/CD、権限管理など追加の運用設計が必要です。

---

問題・機能追加の相談
-------------------
ドキュメントや利用例の追加、特定モジュールの詳しい利用方法（例: ETL のトラブルシュート、OpenAI レスポンス検証方法、監査ログ運用）について必要であれば、対象箇所を指定してご依頼ください。