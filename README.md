# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI 等を組み合わせてデータ取得・品質チェック・特徴量計算・ニュースNLP・市場レジーム判定・監査ログ管理などを提供します。

主な利用対象：
- 日次 ETL（株価・財務・市場カレンダー）の自動化
- ニュースを用いた銘柄センチメント（AIスコア）生成
- 市場レジーム判定（MA200 + マクロニュースの LLM 評価）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- 発注〜約定まで追跡可能な監査テーブルの初期化・管理

---

## 機能一覧（抜粋）

- データ取得 / ETL
  - J-Quants API からの株価（daily_quotes）・財務（statements）・市場カレンダー取得（jquants_client）
  - 差分更新・バックフィル・ページネーション・リトライ・レート制御
  - ETL の高レベル実行（data.pipeline.run_daily_etl）
- データ品質チェック（data.quality）
  - 欠損・スパイク（急変）・重複・日付不整合検出
- カレンダー管理（data.calendar_management）
  - 営業日判定 / 翌営業日・前営業日 / 期間内営業日取得 / JPX カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS フィードからの収集、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存（設計に基づく）
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとにニュースをまとめて LLM（gpt-4o-mini）でセンチメントを算出、ai_scores に書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
  - OpenAI 呼び出しは JSON Mode を利用し、リトライ・フェイルセーフ実装あり
- 研究（kabusys.research）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算・IC 計算・統計サマリー等
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL、初期化ユーティリティ（init_audit_db / init_audit_schema）
- 汎用ユーティリティ
  - 統計正規化（data.stats.zscore_normalize）
  - 環境設定管理（config.Settings）：.env 自動読み込み（プロジェクトルート検出）、必須環境変数取得ヘルパ

設計上の特徴：
- ルックアヘッドバイアスを避ける実装（datetime.today() 等に依存しない）
- 冪等性（ON CONFLICT / idempotent 保存）
- リトライ、バックオフ、API レート制限対応
- DuckDB を主なローカル DB として利用（小〜中規模分析に適合）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に | を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリを取得してインストール（開発モード推奨）
   - (例) git clone してプロジェクトルートで：
     ```bash
     pip install -e .
     ```
2. 必要なパッケージ（主にランタイム依存）
   - duckdb
   - openai (openai SDK)
   - defusedxml
   - これらは pyproject.toml / requirements.txt に記載している想定です。手動で入れる場合:
     ```bash
     pip install duckdb openai defusedxml
     ```
3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みは OS 環境 > .env.local > .env の順）。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード（発注周り利用時）
   - SLACK_BOT_TOKEN : Slack 通知に使用する場合
   - SLACK_CHANNEL_ID : Slack の投稿先チャンネル ID
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector を使う場合）
   - 任意（デフォルトあり）: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL
   - 注意: config.Settings のプロパティが要求するキー名をそのまま使用してください。

5. データフォルダの作成（必要に応じて）
   - デフォルトの DuckDB パス: data/kabusys.duckdb
   - 事前にディレクトリを作るか、init 関数が自動で作成します（audit.init_audit_db は親ディレクトリを自動作成します）。

---

## 使い方（代表的な例）

※ 以下は Python からの利用例です。各関数は duckdb 接続オブジェクト（duckdb.connect("...") が返すもの）を受け取ります。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）をスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定を行う（market_regime に保存）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログDB を初期化してスキーマを作る
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って audit テーブル群が作成されていることを確認できます
```

- RSS を取得して記事一覧を得る（ニュース収集の低レベル API）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点（運用上）：
- OpenAI 呼び出しはコスト・レイテンシに依存します。API キーは必ず安全に管理してください。
- J-Quants API はレート制限があります。jquants_client では固定間隔スロットリングとリトライを実装しています。
- ETL 実行時は品質チェック結果をログ・返却するため、問題があればログと ETLResult を確認してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール（src/kabusys 以下）構成の抜粋：

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / settings 管理（.env 自動読み込みを含む）
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLU / LLM スコアリング
    - regime_detector.py   — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得 / 保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py    — RSS 収集・正規化
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（モメンタム/ボラティリティ/バリュー）
    - feature_exploration.py — 将来リターン・IC・統計サマリー・rank 等
  - research/... (その他ユーティリティ)

（上記は主要な実装ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 主要な設計ノート / 運用上の注意

- Look-ahead bias の回避：
  - AI スコアリングやファクター計算は内部で target_date 未満のデータのみ参照する等、未来データ参照を避ける実装方針です。
- 冪等性：
  - save_* 関数は DB 側で ON CONFLICT DO UPDATE を使い冪等に保存します。
- リトライとバックオフ：
  - OpenAI / J-Quants 呼び出しにはリトライ・指数バックオフを実装しています（ただし API 側での重大エラーはハンドリングが必要）。
- セキュリティ：
  - news_collector には SSRF 対策、XML パースに defusedxml を使用、RSS ペイロード上限の設定等を行っています。
- 自動環境読み込み：
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動で読み込みます。OS 環境変数を優先します。
  - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加したい「使い方のワークフロー（例：日次バッチ cron / systemd サンプル）」や「.env.example のテンプレート」をご希望であれば、その内容を作成します。必要であれば環境変数の詳細な一覧（説明付き）も追加できます。