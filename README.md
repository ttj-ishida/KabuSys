# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース収集・AI によるニュースセンチメント・市場レジーム判定・研究用ファクター計算・監査ログなどを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単な例）
- 環境変数 / .env
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買システムやデータプラットフォームのための共通ライブラリ群です。  
主な設計方針は以下です。
- Look-ahead-bias を避ける設計（内部で `date.today()` などを不用意に使わない）
- DuckDB を用いたローカルデータベース中心の処理
- J-Quants API からの差分取得（レート制限・リトライ・トークン自動更新対応）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（JSON Mode を期待）
- 冪等性 / トランザクション / ロギングを重視した実装

---

## 主な機能（モジュール一覧）
- kabusys.config
  - 環境変数管理、自動 .env ロード機能（プロジェクトルート検出）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline: 日次 ETL パイプライン（prices / financials / calendar の差分取得）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 取得と前処理（SSRF 対策・トラッキング除去等）
  - audit: 監査ログ（signal / order_request / executions）テーブル定義・初期化
  - stats: z-score 正規化など統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースから銘柄別センチメントを計算して `ai_scores` に保存
  - regime_detector.score_regime: ETF (1321) の MA 乖離とマクロニュースから市場レジーム判定
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算・IC・統計サマリー等

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型アノテーションの構文を使用）
- 必要なライブラリ: duckdb, openai, defusedxml（および標準ライブラリ）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（簡易）
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt がある場合はそれを利用してください:
   - pip install -r requirements.txt

3. 開発インストール（パッケージ化されている場合）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須の環境変数（後述）を設定してください。

---

## 環境変数（最小必須）
次の環境変数は多くの処理で必須です。README の用途に応じて `.env` に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN        — Slack 通知に使う場合
- SLACK_CHANNEL_ID       — Slack 通知チャンネル
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注等で使用）

OpenAI:
- OPENAI_API_KEY         — news_nlp / regime_detector の呼び出しで使用（関数呼び出し引数でも注入可）

その他（デフォルトあり）:
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH            — DuckDB 保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH          — 実行監視の PID ファイル（デフォルト: data/execution.pid）

.env 自動読み込みについて:
- プロジェクトルートは本モジュールファイル位置から .git または pyproject.toml を探索して決定します。
- OS 環境変数 > .env.local > .env の優先順位で読み込まれます。

---

## 使い方（代表的な例）

Python REPL やスクリプトから DuckDB 接続を作り、各種関数を呼び出します。

1) DuckDB 接続の準備
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を明示的に指定することで look-ahead を防止できます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコアを計算して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数に渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("ai scores written:", num_written)
```

4) 市場レジーム判定を実行（1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリを自動作成
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))

# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- news_nlp.score_news と regime_detector.score_regime は OpenAI の API を呼び出します。API キーの指定は関数引数か環境変数 OPENAI_API_KEY を使用してください。
- ETL で id_token を明示的に渡すこともできます（テスト時等）。

---

## 監査・品質チェック（概要）
- data.quality.run_all_checks(conn, target_date=..., reference_date=...) を使って欠損・重複・スパイク・日付不整合を検出できます。QualityIssue オブジェクトのリストを返します。
- pipeline.run_daily_etl は品質チェックをオプションで実行し、ETLResult に検出結果を格納します。

---

## 開発・デバッグのポイント
- .env の自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- OpenAI 呼び出しや HTTP クライアントはモジュール内でラッパー関数を用意しており、ユニットテスト時はこれらを patch/mocking で差し替える設計になっています（例: news_nlp._call_openai_api のモック）。
- DuckDB の executemany は空リストを受け付けないバージョン（0.10 系）に合わせたガード（空チェック）を行っています。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要ソースファイル一覧（抜粋）です。

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
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (その他研究用ファイル)
  - research/__init__.py

（上記は本リポジトリに含まれる主要モジュールを抜粋したものです）

---

## 補足: セキュリティ・運用に関する注意
- news_collector は SSRF 対策・レスポンスサイズ上限・XML パース安全化を実装していますが、RSS ソースは信用できるものに限定してください。
- J-Quants API へのリクエストはレート制限（120 req/min）を守る実装です。大量同時実行は避けてください。
- OpenAI 呼び出しはコストとレイテンシがあります。バッチサイズやリトライ設定はパラメータで調整してください。
- 監査ログ（audit テーブル群）は削除しない前提で設計されています。運用ポリシーに合わせてバックアップ・アーカイブを行ってください。

---

もし README に追加したいサンプルスクリプト、より詳しい API リファレンス、あるいは .env.example のテンプレートが必要であれば教えてください。README を用途（開発者向け / 運用者向け / バックテスト用）に合わせて拡張できます。