# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータパイプライン、ニュースNLP、市場レジーム判定、リサーチ（ファクター計算）、
および監査・発注追跡のためのユーティリティ群をまとめたライブラリです。DuckDB をデータ層に用い、
J-Quants / JPX / RSS / OpenAI を利用してデータ収集・前処理・AI スコアリング・ETL を行うことを想定しています。

---

## 主な機能一覧

- データ ETL（J-Quants API からの日次株価・財務・カレンダーの差分取得・保存）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
  - quality.run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- ニュース収集（RSS の安全な取得・前処理・raw_news 保存）
  - news_collector.fetch_rss 等（SSRF/サイズ制限/トラッキング除去などを実装）
- ニュース NLP（OpenAI を利用した銘柄別センチメントスコア）
  - ai.news_nlp.score_news：日次ウィンドウのニュースを銘柄単位でスコアリングし ai_scores に保存
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメントの合成）
  - ai.regime_detector.score_regime：market_regime テーブルに書き込み
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - research.calc_momentum / calc_value / calc_volatility
  - research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 監査ログ / トレーサビリティ（シグナル→発注→約定を追跡する監査スキーマ）
  - data.audit.init_audit_db / init_audit_schema
- J-Quants クライアント（レートリミット・リトライ・トークン管理・DuckDB への冪等保存）
  - data.jquants_client.fetch_* / save_* 系

---

## 前提条件

- Python 3.10+
- duckdb
- openai
- defusedxml
- （ネットワークアクセスが必要：J-Quants, RSS ソース, OpenAI）

pip パッケージ名やバージョンは環境に合わせて適宜指定してください。

---

## セットアップ手順

1. リポジトリをクローン／パッケージを配置
   - 開発時はプロジェクトルートに `pyproject.toml` / `.git` があることを想定しています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそちらを利用）

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（挙動は kabusys.config が管理）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB データベースなどの初期化（任意）
   - 監査DBを初期化する例は下記「使い方」を参照。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score 系で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: one of development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.kabusys.config の .env パーサは以下をサポート:
- export KEY=val 形式
- シングル/ダブルクォートでの値（エスケープ対応）
- 行頭の # はコメント

未設定の必須変数にアクセスすると ValueError になります（Settings クラス経由で取得）。

---

## 使い方（簡単なコード例）

以下はライブラリ内部関数を直接呼ぶ簡単な例です。実運用では例外処理・ロギング・トークン管理を適切に行ってください。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースをスコアリングして ai_scores に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY を設定していれば api_key 引数は不要
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- score_news は前日 15:00 JST 〜 当日 08:30 JST のウィンドウを対象にします（calc_news_window を参照）。
- API 呼び出しは gpt-4o-mini（JSON mode）を想定。

3) 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) リサーチ関数の利用例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

5) 監査DBの初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルに書き込む
```

注意:
- ai モジュールの関数は OpenAI API キー（引数または OPENAI_API_KEY）が必要です。
- 各関数はルックアヘッドバイアス防止のため内部で date.today() を直接参照しない設計になっています（target_date を明示してください）。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み、自動 .env ロードロジック、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py: ニュースの LLM ベースセンチメント評価と ai_scores 書き込み
    - regime_detector.py: ETF 1321 の MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py: 日次 ETL パイプライン（差分取得・保存・品質チェック）
    - etl.py: ETLResult の再エクスポート
    - calendar_management.py: 市場カレンダー管理・営業日判定ヘルパー
    - news_collector.py: RSS 収集・前処理・冪等保存ロジック（SSRF/サイズ制限対策）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py: 監査ログ (signal_events, order_requests, executions) の DDL/初期化
  - research/
    - __init__.py
    - factor_research.py: Momentum / Value / Volatility の計算
    - feature_exploration.py: forward returns / IC / summary / rank など
  - research パッケージは data.stats（zscore_normalize）を利用

---

## 実運用上の注意点（設計方針からの抜粋）

- Look-ahead bias を避けるため、多くの関数は target_date を明示的に受け取り、DB クエリでは date < target_date / date <= ... の条件を慎重に扱っています。
- OpenAI 呼び出しはリトライ・フェイルセーフを備え、API 失敗時はゼロスコアやスキップで継続する設計です（例外を投げずに運用継続を優先）。
- J-Quants クライアントはレートリミット（120 req/min）・リトライ・401 リフレッシュを自動処理します。
- news_collector は SSRF・XML Bomb・大容量レスポンス対策を実装しています。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE／DO NOTHING）で行われます。

---

## 追加情報 / 開発者向けヒント

- .env ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の JSON mode を利用するため、戻り値の厳密な JSON パースを行っています。LLM の応答が不正な場合はロギングしてフォールバック処理を行います。
- DuckDB のバージョン差異に依存しないよう executemany を多用して互換性を保っています（例えば空パラメータの扱い）。

---

ライセンスや貢献方法、サンプルデータや CI 設定などはプロジェクトルートに別途ドキュメントを追加してください。README に記載してほしい追加項目があれば教えてください。