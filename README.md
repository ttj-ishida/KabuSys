# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理などの機能を備え、バックテスト・運用までのデータ基盤と研究ワークフローを支援します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務・カレンダーを差分・ページネーション対応で取得
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）と取得日フェッチ時刻（fetched_at）保存
  - ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（prices / financials / calendar）

- データ品質チェック
  - 欠損（OHLC）・重複・スパイク・日付不整合チェック（quality.run_all_checks）

- ニュース収集・NLP
  - RSS からの安全なニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコア（news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成）（regime_detector.score_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー（research.feature_exploration）
  - クロスセクション Zスコア正規化（data.stats.zscore_normalize）

- 監査（Audit / Tracing）
  - signal → order_request → execution のトレーサビリティ用テーブル定義・初期化（data.audit.init_audit_db / init_audit_schema）

- カレンダー管理
  - JPX マーケットカレンダーの差分更新、営業日判定ユーティリティ（data.calendar_management）

設計上の注力点:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない設計）
- 冪等性（DB 保存や ID トークンキャッシュ）
- フェイルセーフ（外部 API 失敗時は例外を上位に投げず安全に継続するケースあり）
- テストしやすさ（内部 API 呼び出しの差し替え・モックを想定）

---

## 前提・依存

- Python 3.10+（PEP 604 の | 型注釈等を利用しているため）
- 主なパッケージ:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib 等）を使用

必要に応じて pyproject.toml / requirements.txt をプロジェクトで用意してください。

例（インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt / ビルド方法に従ってください
```

---

## セットアップ手順

1. リポジトリをクローン／コピーして Python 環境を準備します。

2. 依存をインストールします（上記参照）。

3. 環境変数（.env）を準備します。
   - 本パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env`、`.env.local` を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト用途など）。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必要な場合）
- SLACK_CHANNEL_ID: Slack チャネル ID（必要な場合）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（ある場合）

任意／デフォルトあり
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: 環境 ('development'|'paper_trading'|'live')（デフォルト: development）
- LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector が必要とする場合）

例: .env（最小）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env.local は .env の override（OS 環境変数は常に最優先）です。

---

## 使い方（主要 API とサンプル）

以下はライブラリを直接インポートして使う例です。用途に応じてスクリプトやジョブに組み込んでください。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ETL を今日分で実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（1日分）を計算して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定されていること
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化（監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 研究用: モメンタム計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の dict のリスト
```

実運用時の注意点:
- news_nlp / regime_detector は OpenAI API を呼び出します。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、API コストと呼び出し制限に注意してください。
- jquants_client は 120 req/min のレートリミットを守るために内部で間隔調整します。ID トークンは自動リフレッシュされます。

---

## ディレクトリ構成（主要ファイル）

（抜粋）src/kabusys 配下:

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
  - etl.py (エクスポート)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit DB 初期化ユーティリティ等
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research や data のユーティリティ群（zscore_normalize 等）

上記は主要モジュールの一覧です。実際のリポジトリ内ではさらに細分化されたファイル群があります。

---

## 設計上の重要なポイント（TODO / 注意）

- ルックアヘッドバイアス回避
  - 多くのモジュールは内部で date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストでは必ず過去データだけを渡してください。

- 冪等保存
  - DuckDB への保存は ON CONFLICT を使って冪等性を担保しています。部分失敗でも既存データの不整合を最小化するロジックがあります。

- テスト可能性
  - OpenAI / ネットワーク呼び出し等は内部で差し替え（モック）可能な関数設計をしています。ユニットテストでは該当関数を patch して孤立させてください。

---

## トラブルシューティング

- .env が読み込まれない
  - 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。プロジェクト構成によってはルートが見つからずスキップされます。その場合は OS 環境変数で直接設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを明示的に無効化してから適切に環境をセットしてください。

- OpenAI / J-Quants 呼び出しでエラーが出る
  - API キーやリフレッシュトークンが正しいか確認してください。何らかの API 側エラー（429/5xx）は内部でリトライ実装がありますが、最終的に失敗した場合は警告ログを出してフォールバックする設計の箇所があります。

---

## 貢献・開発

- バグフィックスや機能追加の PR は歓迎します。設計ドキュメント（StrategyModel.md / DataPlatform.md 等）に沿って実装してください。
- テストは外部 API 呼び出しをモックする形でユニットテストを作成してください。

---

この README はコードベースの公開 API と設計思想を簡潔にまとめたものです。詳しい関数仕様や内部アルゴリズムは各モジュールの docstring を参照してください。必要であればサンプルスクリプトやデプロイ手順（systemd / cron / Docker 等）についても追記できます。