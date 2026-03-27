# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP、マーケットレジーム判定、研究用ファクター計算、監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本市場向けのデータパイプラインおよび自動売買基盤のコア機能群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API からの差分取得（株価、財務、マーケットカレンダー）と DuckDB への冪等保存
- RSS を含むニュース収集と OpenAI を用いたセンチメント評価（銘柄別 ai_score）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究用ファクター（モメンタム／ボラティリティ／バリュー等）計算・探索ツール
- データ品質チェック、監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数による設定管理（.env 自動ロード機能付き）

設計上の重要ポイント:
- ルックアヘッドバイアス対策（date 引数ベースで外部の現在時刻を参照しない）
- DuckDB を中心とした SQL ベース処理（外部ライブラリへの依存を最小化）
- API 呼び出しはリトライ／バックオフ・レート制御を実装して堅牢性を確保
- 各種書き込みは冪等で実行（ON CONFLICT / DELETE→INSERT など）

---

## 機能一覧

- Data / ETL
  - run_daily_etl：日次 ETL（市場カレンダー、日足、財務）を差分更新で実行
  - J-Quants クライアント（fetch / save）：daily_quotes, financial_statements, market_calendar, listed_info
  - market_calendar の更新・営業日判定ユーティリティ
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- News / NLP
  - RSS 取得＆前処理（SSRF 対策・トラッキング除去・gzip 対応）
  - news_nlp.score_news：OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントを ai_scores に書き込み
- AI / レジーム判定
  - regime_detector.score_regime：ETF 1321 の MA とマクロニュースセンチメントを合成して市場レジーム判定を実行
- Research
  - ファクター計算：calc_momentum / calc_volatility / calc_value
  - 特徴量探索：forward returns, IC（Spearman）計算, 統計サマリー、ランク付け
  - zscore 正規化ユーティリティ
- Audit / Execution
  - 監査スキーマ定義と初期化（signal_events, order_requests, executions）
  - init_audit_db / init_audit_schema で DuckDB に監査ログ用テーブルを作成
- 設定管理
  - settings オブジェクト経由で環境変数を型安全に取得（自動 .env ロードあり）
  - 必須環境変数未設定時は例外を発生

---

## 必要条件

- Python 3.10 以上（型付けに `|` を使用しているため）
- 主な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリのみで実装を心がけていますが、環境に応じて追加インストールが必要になる場合があります。

requirements.txt を用意している場合はそれに従ってください。なければ最低限次をインストールしてください:
pip install duckdb openai defusedxml

---

## 環境変数

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL / jquants_client 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 関連）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID

任意またはデフォルト有り:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI 呼び出し用（news_nlp / regime_detector でも引数経由で指定可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env を読み込む処理を無効化できます（テスト時に便利）。

自動 .env 読み込みについて:
- プロジェクトルートはこのモジュールの位置から上方向に .git または pyproject.toml を探索して決定します。
- 読み込み順序: OS 環境変数（最優先） > .env.local（上書き） > .env（下位）。.env.local は .env を上書きします。
- .env のパースはシェル風の方式（export 句やクォート・コメント処理）に対応しています。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトで requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を作成
   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development

   - テスト実行時など自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB ファイル等の準備
   - デフォルトでは data/kabusys.duckdb を使用します。必要に応じて settings.duckdb_path を変更してください。
   - 監査DB用に init_audit_db を呼ぶと監査テーブルが作成されます（自動で親ディレクトリを作成します）。

---

## 使い方（簡単なコード例）

以下は Python REPL / スクリプト上での基本的な呼び出し例です。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 環境変数が必要
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # テーブルとインデックスを作成して接続を返す
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(f"取得レコード数: {len(records)}")
```

注意:
- OpenAI 呼び出しを行う関数（score_news, score_regime）は API 呼び出しリトライやエラーフォールバックを持ちますが、API キーの準備・コスト管理はユーザ側で行ってください。
- ETL / save 関数は DuckDB のテーブルスキーマが期待どおりに作成されていることを前提とします（Schema 初期化手順が別途ある場合は先に実行して下さい）。

---

## 開発者向けメモ

- 自動 .env 読み込みはパッケージロード時に行われます（kabusys.config モジュール）。テストで副作用を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI クライアントの低レイヤ呼び出し関数はテスト時に patch 可能（各モジュール内の `_call_openai_api` をモックする）。
- J-Quants クライアントは内部で RateLimiter とトークンキャッシュを持ち、401 のときの自動リフレッシュロジックを備えています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化（version, __all__）
- config.py — 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）

src/kabusys/ai/
- __init__.py — AI モジュールの公開関数
- news_nlp.py — ニュース記事の集約・OpenAI による銘柄別センチメント評価（score_news）
- regime_detector.py — ETF MA + マクロニュースを合成した市場レジーム判定（score_regime）

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
- pipeline.py — ETL パイプラインと run_daily_etl
- etl.py — ETL の公開型（ETLResult の再エクスポート）
- news_collector.py — RSS 取得 / 前処理 / raw_news 保存
- calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
- quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
- stats.py — zscore_normalize など統計ユーティリティ
- audit.py — 監査ログ（schema 定義・初期化）
- その他：（必要に応じて追加の実装ファイル）

src/kabusys/research/
- __init__.py — 研究 API の公開
- factor_research.py — モメンタム / ボラティリティ / バリュー計算
- feature_exploration.py — 将来リターン / IC / 統計サマリー / rank

---

## ライセンスと貢献

- ライセンス情報はプロジェクトルートにある LICENSE / pyproject.toml を参照してください（存在する場合）。
- バグ報告・機能提案は Issue を立ててください。プルリク歓迎です。

---

README に書かれている各 API はコード内に詳細な docstring と設計方針が記載されています。実運用やバックテストで使う際は、特に「Look-ahead Bias 回避」「環境変数・API キー管理」「DB スキーマの初期化」を遵守して下さい。必要であれば README を拡張して、schema 初期化 SQL の手順や CI / デプロイ手順も追記できます。