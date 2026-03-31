# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（audit）などを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要なユースケースとサンプルコード）
- 環境変数（主要な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォームでよく使う処理をまとめたライブラリです。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、財務、カレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS ニュース収集・NLP による銘柄センチメント算出（OpenAI）
- マーケットレジーム判定（ETF + マクロニュースを統合）
- 研究用途のファクター計算・特徴量評価ユーティリティ
- 発注・約定に関する監査ログ用スキーマ初期化（監査トレース）

設計上の方針としては「ルックアヘッドバイアスを避ける」「冪等性」「フォールバックとフェイルセーフ」を重視しています。

---

## 機能一覧

- data
  - jquants_client: J-Quants API 呼び出し・保存（fetch / save）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定とカレンダー更新ジョブ
  - news_collector: RSS 取得・正規化・raw_news 保存（SSRF 対策・トラッキング除去）
  - audit: 監査ログテーブルの DDL と DB 初期化ユーティリティ
  - stats: z-score 正規化ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI にて算出し ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター算出（calc_momentum, calc_volatility, calc_value）
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリー、ランク関数など
- config
  - 環境変数読み込みロジック（.env / .env.local の自動ロード、必須チェック）

---

## セットアップ手順

前提: Python 3.9+（duckdb 等の要件に合わせる）を想定しています。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール  
   （このコードベースでは少なくとも以下が必要です）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では requirements.txt や pyproject.toml を用意してください。

4. パッケージを開発モードでインストール（オプション）
   ```
   pip install -e src
   ```

5. 環境変数設定  
   プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

---

## 環境変数（主要な設定）

必須（システムの多くの機能で必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- KABU_API_PASSWORD: kabu ステーション API を使う場合のパスワード

OpenAI 関連:
- OPENAI_API_KEY: news_nlp / regime_detector の OpenAI 呼び出しに使用（関数引数で直接渡すことも可）

その他（任意 / デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT などの監視設定

注意: Settings クラスが未設定の必須キーを参照すると ValueError を投げます。

---

## 使い方（主要ユースケース・サンプル）

以下は最小限の使用例です。適宜例外処理・ログ設定を追加してください。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコア算出（OpenAI API キーは env に設定するか api_key を渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} ai_scores")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って発注/監査ログ関連の操作を行う
```

5) J-Quants の生 API 呼び出し（認証）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
```

---

## 自動 .env ロードについて

- パッケージ起動時に .env（プロジェクトルート）を自動で読み込みます。優先順位は OS 環境変数 > .env.local > .env です。
- 自動ロードの検出はこのファイルの場所から親ディレクトリを順に見て .git または pyproject.toml を見つけたディレクトリをプロジェクトルートとして扱います。
- 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例（.env.example として用意してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - quality.py             — 品質チェック
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS 収集／正規化
    - audit.py               — 監査ログ DDL / 初期化
    - stats.py               — 共通統計ユーティリティ
    - etl.py                 — ETLResult 再エクスポート
    - pipeline.py            — ETL 本体
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン / IC / summary / rank

各モジュールはドキュメント文字列とログ出力を豊富に備えており、外部参照（DuckDB コネクション／OpenAI クライアントなど）を注入してテストしやすく作られています。

---

## 補足・運用上の注意

- OpenAI 呼び出し（news_nlp / regime_detector）は API 失敗時にフェイルセーフで処理を継続する設計です（スコアを 0 にフォールバック等）。ただし API キーは必須で、明示的に渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- jquants_client はレートリミット（120 req/min）・リトライ・401 トークンリフレッシュに対応しています。ID トークンは内部キャッシュされます。
- DuckDB に対する executemany の空リストはバージョン依存で問題になるため、コード側で空チェックを行っています。
- 監査ログ（audit）スキーマは冪等に作成されます。init_audit_db() は必要に応じて transactional=True を渡せますが DuckDB のトランザクションの性質に注意してください。

---

問題・改善点の報告や使い方で不明点があれば教えてください。README を実際の環境（依存ファイル・CI 設定など）に合わせてカスタマイズすることもできます。