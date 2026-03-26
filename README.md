# KabuSys

バージョン: 0.1.0

日本株のデータ基盤・リサーチ・AIスコアリング・監査ログを統合する自動売買支援ライブラリです。J-Quants / RSS / OpenAI / DuckDB を組み合わせ、ETL、品質チェック、ニュースセンチメント解析、市場レジーム判定、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群を含みます:

- データ取得と差分 ETL（J-Quants API 経由で日足・財務・市場カレンダーを取得し DuckDB に保存）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア算出（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム/バリュー/ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）用のスキーマ初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス対策（datetime.today()/date.today() を不適切に参照しない設計）
- DuckDB を主要なオンディスク DB として使用（軽量で SQL 利用可能）
- OpenAI 呼び出しは JSON Mode（厳密な JSON レスポンス想定）で実装、リトライやフォールバックあり
- ETL は差分更新・バックフィル・品質チェックを行い、部分失敗に配慮

---

## 主な機能一覧

- ETL: data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント: data.jquants_client.fetch_* / save_*（rate limit / retry / token refresh 対応）
- ニュース収集: data.news_collector.fetch_rss（SSRF / gzip / トラッキング除去 等に配慮）
- ニュース NLP: ai.news_nlp.score_news（銘柄ごとに LLM でセンチメントを算出して ai_scores に保存）
- レジーム判定: ai.regime_detector.score_regime（ETF 1321 の MA200 乖離 + マクロ記事の LLM スコア）
- 研究用: research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- データ品質: data.quality.run_all_checks（欠損・重複・スパイク・日付不整合検出）
- 監査ログ初期化: data.audit.init_audit_db / init_audit_schema
- 設定管理: config.Settings（.env 自動ロード、環境変数アクセスのラッパー）

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+（typing の union などを使用）を推奨します。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （任意）pip install -e .  <-- パッケージを editable インストールする場合

   ※ 実行環境によっては追加パッケージが必要になる場合があります。requirements.txt がある場合はそちらを利用してください。

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（data.jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等と連携する場合）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知等）
- SLACK_CHANNEL_ID: Slack チャネル ID

その他（任意／デフォルトあり）:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）

例 (.env)
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxxx
    KABU_API_PASSWORD=secret
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development

---

## 使い方（主要なユースケース例）

以下は Python REPL / スクリプトからの利用例です。

1) DuckDB 接続を開いて日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 対象日を指定しない場合は今日が対象（設計上は ETL 内で営業日調整あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを生成する（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数でセットされているか、api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"スコア付与済み銘柄数: {count}")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が必要（api_key 引数でも渡せる）
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成してスキーマを初期化（:memory: も可）
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続オブジェクト
```

5) 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト（各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev など）
```

6) データ品質チェックを実行
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## 自動 .env 読み込みの挙動

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、デフォルトで自動で .env と .env.local を読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に推奨）。

.env のパースはシェル形式（export KEY=val など）やクォート・エスケープにも対応しています。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと簡単な説明です（リポジトリ直下は src/kabusys 以下）:

- src/kabusys/__init__.py
  - パッケージメタ情報（バージョン、公開サブパッケージ名）

- src/kabusys/config.py
  - 環境変数 / .env の自動ロードと Settings ラッパー

- src/kabusys/ai/
  - news_nlp.py : ニュースの LLM センチメントスコアリング（ai_scores 書き込み）
  - regime_detector.py : ETF MA200 とマクロニュースを合成した市場レジーム判定

- src/kabusys/data/
  - __init__.py
  - pipeline.py : ETL のメインロジック（run_daily_etl 等）
  - jquants_client.py : J-Quants API クライアント（取得・保存・レート制限・リトライ）
  - news_collector.py : RSS フィード収集、前処理、raw_news 保存ロジック
  - calendar_management.py : 市場カレンダー管理 / 営業日判定 / calendar_update_job
  - stats.py : z-score 正規化等の統計ユーティリティ
  - quality.py : データ品質チェック (欠損/スパイク/重複/日付不整合)
  - audit.py : 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - etl.py : ETLResult の再エクスポート

- src/kabusys/research/
  - factor_research.py : モメンタム/バリュー/ボラティリティ等のファクター算出
  - feature_exploration.py : 将来リターン計算、IC/ランク/統計サマリー等
  - __init__.py : 研究用ユーティリティの公開

- src/kabusys/ai/__init__.py
  - ai モジュールの公開 API（score_news など）

---

## 運用上の注意点

- OpenAI 呼び出しは API 失敗時にフォールバック（スコア 0.0）する設計ですが、実稼働では API キーと呼び出し量の管理（コスト・レート制限）を行ってください。
- ETL は差分更新と部分的な再フェッチ（バックフィル）を行います。最初の初期ロードは長時間かかる場合があります。
- DuckDB のファイルはバックアップしてください。監査ログやメインデータベースは消失に注意が必要です。
- 監査ログスキーマは冪等的に作成しますが、テーブル削除/スキーマ変更は慎重に行ってください。
- news_collector は外部 URL 取得を行うため SSRF 対策や最大受信サイズ等の安全措置を実装していますが、信頼できるホワイトリスト運用を推奨します。

---

## 貢献・開発

- 新しい機能追加・バグ修正は Pull Request をしてください。
- テストはユニットテストを追加し、特にネットワーク呼び出し部分はモック化してテストすることを推奨します（モジュール内の _call_openai_api や _urlopen 等はテスト差し替えを想定した設計になっています）。

---

必要であれば、この README に含める具体的な .env.example や CLI スクリプト、requirements.txt のテンプレートを生成できます。どの形式がよいか教えてください。