# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README（日本語）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ファクター計算、ニュース NLP によるセンチメント解析、監査ログの管理、ETL パイプラインなどを統合したライブラリ群です。DuckDB をデータレイヤに用い、OpenAI（gpt-4o-mini）をニュース解析に利用するモジュールを含みます。バックテストや自動売買システムの基盤を構築するためのユーティリティ群を提供します。

設計上の特徴：
- Look-ahead バイアス回避（内部で date.today() 等を直接参照しない設計）
- 冪等性を配慮した DB 書き込み（ON CONFLICT 等）
- API 呼び出しに対するリトライ／レート制御を実装
- ニュース収集で SSRF 対策や受信サイズ制限を実装

---

## 機能一覧

主なモジュールと機能（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - アプリ設定（API トークン、DB パス、監視閾値等）

- kabusys.data
  - jquants_client：J-Quants API クライアント、データ取得・DuckDB 保存
  - pipeline：日次 ETL 実行（run_daily_etl）
  - quality：データ品質チェック（欠損、重複、スパイク、日付整合性）
  - calendar_management：JPX カレンダー管理・営業日判定
  - news_collector：RSS からのニュース収集（SSRF 対策・テキスト前処理）
  - audit：監査ログ（signal / order_request / executions）テーブル初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news：ニュースを LLM で解析し銘柄ごとの ai_score を生成・保存
  - regime_detector.score_regime：ETF（1321）の MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定・保存

- kabusys.research
  - factor_research：モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration：将来リターン計算、IC（Information Coefficient）、統計サマリ、ランク化ユーティリティ

- kabusys.data.stats
  - zscore_normalize：クロスセクションでの Z スコア正規化

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に Python 3.10 の union タイプ記法を使用）
- システムに pip が使えること

推奨インストール手順（リポジトリルートで実行）：

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - requirements.txt が無い場合、最低限以下をインストールしてください：
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトではその他 logging や DB 用ユーティリティ等が必要になる場合があります。パッケージロック／requirements をプロジェクトに合わせて用意してください。

3. 環境変数設定
   - .env（または .env.local）をプロジェクトルートに置くと自動で読み込まれます（詳細は下記「環境変数」参照）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. DuckDB ファイルの初期化（監査 DB 等）
   - 監査テーブルを初期化するには Python から:
     ```py
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)
     ```
   - ：memory: を使えばインメモリ DB が得られます。

---

## 使い方（簡易サンプル）

以下は代表的な利用例です。実用時はエラーハンドリングやログ設定を行ってください。

1) ETL（日次パイプライン）の実行
```py
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコア生成（AI）
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定していれば api_key は不要
n = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n}")
```

3) 市場レジーム判定（AI + MA）
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

4) ファクター計算例
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records))
```

5) 監査スキーマの初期化（既存接続へ追加）
```py
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 環境変数（.env）

config.Settings が参照する主な環境変数

必須（実行する機能に応じて設定）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD
  - kabuステーション API パスワード（注文系を使用する場合）
- SLACK_BOT_TOKEN
  - Slack へ通知する場合に使用する BOT トークン
- SLACK_CHANNEL_ID
  - Slack チャンネル ID（通知送信先）

OpenAI 関連
- OPENAI_API_KEY
  - kabusys.ai.news_nlp / regime_detector が使用します（関数呼び出し時に api_key を直接渡すことも可）

任意・デフォルト値あり
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH — デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（パーセント）

.env 自動読み込みについて
- プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を起点に .env と .env.local を自動ロードします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テストなどで利用）。

---

## ディレクトリ構成（主要ファイルのみ抜粋）

src/kabusys/
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
  - etl.py (pipeline の再エクスポート)
  - quality.py
  - calendar_management.py
  - news_collector.py
  - stats.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

説明:
- data/jquants_client.py: J-Quants API からのデータ取得・DuckDB 保存処理
- data/pipeline.py: 日次 ETL の実行ロジック（run_daily_etl）
- ai/news_nlp.py / ai/regime_detector.py: OpenAI を用いたニュース解析・市場レジーム判定
- research/*: ファクター計算・IC 計算などの研究用ユーティリティ
- data/audit.py: 監査ログ用テーブルの DDL と初期化ヘルパー

---

README はここまでです。実際に導入する際は、インフラ（API トークンや DB の配置）、ログ設定、運用監視（プロセス管理や Slack 通知）を適切に構成してください。必要であれば、各モジュールの詳細ドキュメント（関数引数・戻り値・副作用）や実運用時の推奨設定例も作成します。必要なら次にどのドキュメントを生成するか教えてください。