# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ニュース収集／NLP（OpenAI）、研究用ファクター計算、ETL パイプライン、監査ログ、マーケットカレンダー等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群をまとめたパッケージです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）およびマクロセンチメントを含めた市場レジーム判定
- Research 向けファクター計算（モメンタム／ボラティリティ／バリュー等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を担う監査 DB 初期化ユーティリティ
- 環境変数／設定管理（.env 自動読み込み・上書きポリシー）

設計上、ルックアヘッドバイアスを避けるため、内部で現在時刻を安易に参照せず、外部から target_date を注入して処理を行う方針を採っています。

---

## 機能一覧（抜粋）

- 環境設定: 自動 .env ロード（.env.local を優先）、必須キーチェック（kabusys.config）
- ETL パイプライン: run_daily_etl・個別 ETL（prices/financials/calendar）と ETL 結果オブジェクト（kabusys.data.pipeline）
- J-Quants クライアント: ページネーション対応、レートリミット、トークン自動リフレッシュ、DuckDB への冪等保存（kabusys.data.jquants_client）
- ニュース収集: RSS 取得・前処理・SSRF 対策、raw_news への保存（kabusys.data.news_collector）
- ニュース NLP: OpenAI で銘柄ごとセンチメントを算出して ai_scores へ保存（kabusys.ai.news_nlp）
- 市場レジーム判定: ETF (1321) の MA200 とマクロニュースセンチメントを合成（kabusys.ai.regime_detector）
- 研究ツール: ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリー（kabusys.research）
- データ品質チェック: 欠損・重複・スパイク・日付整合性（kabusys.data.quality）
- カレンダー管理: 営業日判定／next/prev_trading_day／calendar_update_job（kabusys.data.calendar_management）
- 監査ログ: 監査スキーマ作成・監査 DB 初期化（kabusys.data.audit）

---

## 必要条件 / 依存ライブラリ

（実際の setup.py / pyproject.toml に合わせてください。ここは主要なランタイム依存の例です）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -r requirements.txt
   - もしくは最低限: pip install duckdb openai defusedxml

4. パッケージをインストール（開発モード推奨）
   - pip install -e .

5. 環境変数の準備
   プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。

   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
   - SLACK_BOT_TOKEN — Slack 通知用（使用箇所がある場合）
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - KABU_API_PASSWORD — kabuステーション等と連携する場合のパスワード（発注系）
   - OPENAI_API_KEY — OpenAI を利用する場合（score_news / score_regime にデフォルトで使用）

   任意／デフォルト値:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

6. DuckDB スキーマや監査 DB の初期化
   - 監査ログを使う場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - ETL 用のメイン DB は ETL 実行時に必要なテーブルが存在することが前提です。スキーマ初期化関数がある場合はそれを呼んでください（コードベースに schema 初期化ユーティリティがあれば利用）。

---

## 使い方（短いコード例）

以下は Python REPL やスクリプトから利用するサンプルです。

- 設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続を開いて日次 ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（1321 の MA200 とマクロセンチメントの合成）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへ書き込み等を行う
```

ノート:
- score_news / score_regime は OpenAI 呼び出しを伴うため API キーとネットワークアクセスが必要です。テスト時はモック化が想定されています（モジュール内で _call_openai_api を patch する設計）。

---

## 環境変数の挙動

- 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動ローディングはパッケージ内でプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行われます。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py — パッケージ初期化（公開サブパッケージ定義）
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（銘柄別スコア）と OpenAI 呼び出し・バッチ処理
    - regime_detector.py — 市場レジーム判定（ETF 1321 MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - pipeline.py — ETL パイプラインと ETLResult
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・SSRF 対策
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック
    - stats.py — 共通統計ユーティリティ（zscore）
    - audit.py — 監査ログスキーマ・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - ai/*, data/*, research/* は相互に最小限の結合で設計されています（テストしやすさを重視）。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策: 多くの処理は target_date を引数で受け取り、内部で date.today() を安易に使わない設計です。バックテストや再現のために必ず明示的な日付を渡してください。
- API リトライ・フェイルセーフ: OpenAI や J-Quants の呼び出しはリトライやタイムアウト処理が入っています。外部 API 失敗時にもプロセスが継続することを目指しています（ただし、重要な値が取れない場合はスコアが 0.0 等にフォールバックされます）。
- DuckDB との互換性: DuckDB の executemany の制約等に配慮した実装が行われています（空リスト渡し回避など）。
- セキュリティ: news_collector は SSRF 対策（プライベート IP 検査、リダイレクト検査）や XML の安全パーサ（defusedxml）を使用しています。

---

## 貢献 / テスト

- ユニットテスト・モック化が容易になるように、外部 API 呼び出し箇所（例: _call_openai_api, _urlopen, J-Quants の HTTP 呼び出し）を patch してテストする設計になっています。
- 変更を加える場合は、DuckDB のスキーマとデータ操作に注意して単体テストを追加してください。

---

必要であれば README にサンプル .env.example や詳細な DB スキーマ、起動スクリプト（systemd / cron などでの ETL 実行例）を追加します。どの情報をさらに充実させたいか教えてください。