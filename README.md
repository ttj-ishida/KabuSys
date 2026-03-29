# KabuSys

日本株向けのデータプラットフォーム＆自動売買基盤のコアライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、リサーチ（ファクタ計算・特徴量探索）、監査ログ（トレーサビリティ）、市場レジーム判定などの機能を含みます。

---

## 主要な特徴（ざっくり）

- データ取得（J-Quants API）と差分ETL（DuckDB への冪等保存）
- ニュース収集（RSS）とテキスト前処理、LLM を用いた銘柄別センチメントスコアリング
- 市場レジーム判定（ETF の MA200 とマクロニュースセンチメントの合成）
- ファクター計算（Momentum / Value / Volatility 等）および特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査用スキーマ（signal→order_request→execution のトレース）
- 環境変数ベースの設定管理（.env 自動読み込みをサポート）

---

## 要件

- Python 3.10+
- ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を明記してください。

---

## セットアップ手順（例）

1. リポジトリをクローン／配置
   - （パッケージ化されている想定）ソースをディレクトリに置きます。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - 他に必要なパッケージがあれば追加でインストールしてください。

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数例（最低限）：
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xxxxx
     - SLACK_CHANNEL_ID=xxxxx
     - OPENAI_API_KEY=xxxxx
   - 任意 / デフォルトあり：
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 .env ロードを無効化）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi

.env の読み込みは以下規則で行われます（自動ロード有効時）:
- OS 環境変数 > .env.local > .env の優先順で設定されます。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを止めることができます。

---

## 使い方（主要なユースケース）

下記は最小限の呼び出し例です。DuckDB 接続は `duckdb.connect()` を利用します。

注意：各 API は例外を投げることがあるため実運用ではログ・例外処理を入れてください。

1) ETL（日次 ETL パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path も利用可
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコア（銘柄別 ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```
- 内部で OpenAI API を使用します。OPENAI_API_KEY を環境変数に設定するか、引数 api_key で渡します。

3) 市場レジーム判定（market_regime テーブルへの書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```
- ETF 1321 の MA200 とマクロニュースセンチメントを合成します。OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で提供してください。

4) 監査ログ（監査用 DB）を初期化する
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# 以降 conn で監査テーブルを利用できます
```

5) 市場カレンダー更新ジョブ（差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存レコード数: {saved}")
```

---

## 設定（環境変数一覧 — 少なくとも知っておくもの）

- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

環境変数の取得・必須チェックは `kabusys.config.settings` を通じて行えます。

---

## 開発者向けノート

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出しは各モジュール内でラップされており、テスト時は該当内部関数を mock して差し替えられるよう設計されています（例: unittest.mock.patch）。
- データベース操作（DuckDB）は多くの関数で BEGIN/COMMIT/ROLLBACK を用いた冪等・トランザクション処理を行っています。DuckDB のバージョン依存の振る舞いに注意してください（例: executemany の空リスト取り扱いなど）。
- Look-ahead バイアス対策: 多くの処理は `date` 引数で基準日を明示し、内部で `date.today()` に頼らない設計です。バックテスト等ではこの方針に従ってください。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research サブパッケージは zscore 正規化やファクター計算・特徴量解析を提供します。
- data サブパッケージは ETL、カレンダー管理、データ品質チェック、J-Quants クライアント、RSS ニュース収集、監査ログ初期化などを含みます。
- ai サブパッケージはニュースセンチメント評価と市場レジーム判定を提供します。

（上記は本コードベースに含まれる主要モジュールの抜粋です）

---

## 追加情報 / 注意点

- OpenAI の利用はコストが発生します。API 呼び出しはバッチ化、リトライ、フェイルセーフ（失敗時は 0.0 を返す等）を取り入れていますが、運用前に費用・レイテンシの確認を行ってください。
- J-Quants API はレート制限を守る必要があります。本クライアントは固定間隔スロットリングとリトライを備えていますが、運用環境ではさらに監視を行ってください。
- 本パッケージはバックテストや実取引に用いる場合、適切な安全対策（資金管理、二重発注防止、テスト環境での動作確認）を必ず行ってください。

---

ご要望があれば、README に含める例（.env.example の具体例、Docker / systemd サービス設定、CI 用のテスト実行手順等）を追加で作成します。