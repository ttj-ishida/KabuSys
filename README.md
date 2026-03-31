# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチ向けライブラリ群です。  
J-Quants からのデータ取得（ETL）・DuckDB によるデータ管理・ニュースの NLP スコアリング（OpenAI）・市場レジーム判定・監査ログ／発注トレーサビリティなどを備え、研究〜本番運用までを想定した設計になっています。

主な特徴
- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）および品質チェック
- DuckDB をデータレイヤに利用した高速な SQL ベース処理
- ニュース記事の収集・前処理・LLM（OpenAI）による銘柄別センチメント付与
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ
- 研究用ファクター計算・特徴量探索ユーティリティ（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 冪等性・レート制御・リトライ等の実運用向け配慮

---

## 機能一覧（抜粋）

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、ページネーション、レート制限、保存関数）
  - market calendar 管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（欠損・スパイク・重複・日付チェック）
  - audit（監査ログスキーマ初期化 / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news（ニュースを LLM に送り ai_scores に書き込む）
  - regime_detector.score_regime（ETF MA とマクロニュースで市場レジーム判定）
- research/
  - factor_research（モメンタム / バリュー / ボラティリティ）
  - feature_exploration（将来リターン計算 / IC / 統計サマリー）
- config.py
  - 環境変数の自動ロード（.env / .env.local）と Settings 抽象化（必須値検査）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止

設計上の要点
- ルックアヘッドバイアス防止：date 引数ベースで処理し、datetime.today()/date.today() を直接参照しない設計箇所が多い
- 冪等性：DB への保存は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT パターンを利用
- 運用配慮：API レート制御、リトライ（指数バックオフ）、トークン自動リフレッシュ等

---

## 前提 / 要求環境

- Python 3.10+（typing の | シンタックスなどを使用）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS）

requirements.txt は本リポジトリに含まれていない想定のため、環境に応じてインストールしてください。

例:
pip install duckdb openai defusedxml

（プロジェクト配布形態に合わせて pip install -e . などを用いてください）

---

## セットアップ手順

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成して有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）
   pip install -r requirements.txt

4. 環境変数を設定
   プロジェクトルートに .env（または .env.local）を置くと自動的に読み込まれます（config.py 内の自動ロード）。
   自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必要となる主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN        … J-Quants 用リフレッシュトークン（必須）
   - KABU_API_PASSWORD            … kabu API パスワード（必須）
   - SLACK_BOT_TOKEN              … Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID             … Slack チャンネルID（必須）
   - OPENAI_API_KEY               … OpenAI API キー（LLM を使う処理で必須）
   - DUCKDB_PATH                  … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH                  … sqlite（監視用）パス（デフォルト: data/monitoring.db）

   注: config.Settings のプロパティを参照すると未設定時に ValueError が発生します（必須チェック）。

5. データディレクトリ等を作成（必要に応じて）
   mkdir -p data

---

## 使い方（ライブラリとしての呼び出し例）

このライブラリは CLI ではなくモジュール群です。Python スクリプトや Scheduler（cron / systemd timer / Airflow 等）から関数を呼び出して利用します。

1) DuckDB 接続を作って ETL を実行する例

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を None にすると本日を対象にします（ただし内部で日時参照の箇所がある点に注意）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))

2) ニュースを LLM でスコアリング（OpenAI API 必須）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")

3) 市場レジーム判定（1321 の MA とマクロ記事の合成）

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定しておく

4) 監査ログ DB 初期化（監査用専用 DB を作る）

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル（signal_events, order_requests, executions 等）が作成されます

5) RSS フィードを取得するユーティリティ（単体）

from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])

注意点
- LLM（OpenAI）を利用する関数は api_key 引数で直接キーを渡すか、環境変数 OPENAI_API_KEY を設定する必要があります。
- J-Quants の API 呼び出しは rate limit（120 req/min）やトークン更新を内部で扱いますが、API キー（JQUANTS_REFRESH_TOKEN）は必須です。
- ETL / 保存処理は冪等に設計されていますが、DuckDB のバージョン依存の細かい挙動（executemany 空リスト禁止など）に注意しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み、自動ロードロジック、Settings クラス（必須変数チェック）
- ai/
  - __init__.py
  - news_nlp.py          … ニュースの LLM スコア付与（score_news）
  - regime_detector.py   … 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    … J-Quants API クライアント（fetch_*, save_*）
  - pipeline.py          … ETL パイプライン（run_daily_etl 等）
  - etl.py               … ETLResult 再エクスポート
  - calendar_management.py … market_calendar 管理（営業日判定等）
  - news_collector.py    … RSS 取得・前処理・SSRF 対策
  - quality.py           … データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py             … zscore_normalize 等の汎用統計
  - audit.py             … 監査ログ（DDL / init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py   … Momentum/Value/Volatility 計算
  - feature_exploration.py … 将来リターン, IC, 統計サマリー
- research/...           … 研究・解析ユーティリティ群
- その他モジュール（execution, strategy, monitoring 等はパッケージ公開対象として __all__ に含められている想定）

---

## 実運用上の留意点

- 環境変数未設定時: config.Settings の必須プロパティは未設定で ValueError を投げます。デプロイ前に .env を用意してください（.env.example を参照する想定）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。CWD に依存しない点に留意してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます（テスト時に便利）。
- OpenAI 呼び出しや J-Quants API 呼び出しは外部サービスに依存します。API 差分やレート制限、ネットワーク障害に備えて監視・リトライポリシーの設定・ログ収集を行ってください。
- DuckDB のファイルパス権限・バックアップ、監査 DB の保管ポリシーは運用環境に合わせて管理してください。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が設定されていない
  - 必須環境変数（JQUANTS_REFRESH_TOKEN など）を .env に追加してください。
- OpenAI API 呼び出しで失敗する
  - OPENAI_API_KEY を確認。ネットワーク・料金制限も確認してください。
- J-Quants API で 401 が出る
  - refresh token が無効化されている可能性。JQUANTS_REFRESH_TOKEN を確認・更新してください。
- RSS 取得で SSL/接続エラーや SSRF 関連の例外が発生する
  - fetch_rss はリダイレクト先の検査やプライベートアドレスチェックを行います。許容されていないホストへのアクセスは失敗します。

---

必要であれば、README に以下の情報も追加できます：
- 詳細な .env.example（各キーの雛形）
- requirements.txt の候補リスト
- 実行用の簡易 CLI（例: run_etl.py）や systemd / cron 用のサンプル unit ファイル
- テスト・CI 設定例（unittest のモック例、外部 API をモックする方法）

追加で書きたい項目や、.env のサンプルなどが必要であれば教えてください。