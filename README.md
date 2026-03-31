# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。ETL による J-Quants からのデータ取得、ニュースの収集・NLP スコアリング、ファクター計算（リサーチ）、監査ログ（発注→約定のトレース）、マーケットカレンダー管理などを包含します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「堅牢なリトライ／フォールバック」であり、DuckDB をデータ格納先に、OpenAI（gpt-4o-mini）をニュースの NLP に利用する設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API と実行例）
- ディレクトリ構成
- 知っておくべき注意点

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ生成を行うためのモジュール群です。J-Quants API を介して株価・財務・市場カレンダーを取得し、DuckDB に保存・加工します。ニュースは RSS から収集し、OpenAI を使って銘柄ごとのセンチメントやマクロセンチメントを算出します。研究用のファクター計算や IC 計算ユーティリティも含みます。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（優先度: OS 環境 > .env.local > .env）
  - 必須設定チェック（未設定時は ValueError）

- データ ETL（jquants_client / pipeline）
  - J-Quants API から日次株価（OHLCV）、財務データ、市場カレンダーを差分取得
  - レートリミット遵守・リトライ実装・ID トークン自動リフレッシュ
  - 差分 ETL 実行用の run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl

- データ品質チェック（data.quality）
  - 欠損、重複、将来日付、スパイク（前日比閾値）などの検出
  - QualityIssue オブジェクトで結果を返す（error / warning）

- ニュース収集（data.news_collector）
  - RSS からの記事取得、前処理、SSRF 対策、トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存を想定

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）により、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む（バッチ処理・リトライ・レスポンス検証）
  - calc_news_window: 対象ニュースの時間ウィンドウ計算（JST ベース）

- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で 'bull' / 'neutral' / 'bear' を判定して market_regime テーブルへ保存
  - OpenAI 呼び出しのリトライ・フェイルセーフ実装

- リサーチユーティリティ（research）
  - ファクター計算: momentum（1/3/6M 等）, volatility（ATR）, value（PER/ROE）
  - 将来リターン計算（calc_forward_returns）
  - IC（Information Coefficient）計算、ランク付け、統計サマリー
  - zscore_normalize（data.stats）によるクロスセクション正規化

- 監査ログ（data.audit）
  - signal_events, order_requests, executions のテーブル定義と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を初期化（UTC タイムゾーン固定）

---

## セットアップ手順

前提
- Python 3.10 以上（typing に Path | None 等を使用）
- DuckDB を利用（Python パッケージ duckdb）
- OpenAI API を使用する場合は openai（あるいは OpenAI の新 SDK）を導入
- RSS パース等に defusedxml を使用

推奨インストール例（プロジェクトルートで）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）

3. パッケージのインストール（開発モード）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（src と同じルート想定）に .env または .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- OPENAI_API_KEY         : （ai モジュールを使う場合）OpenAI API キー
- KABU_API_PASSWORD     : kabu ステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合
- DUCKDB_PATH           : デフォルト data/kabusys.duckdb（お好みで変更）
- SQLITE_PATH           : 監視用 sqlite（デフォルト data/monitoring.db）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方

以下に代表的な実行例を示します。各関数は DuckDB の接続（duckdb.connect(...) の戻り値）を受け取ります。

1) DuckDB に接続する
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成されます
```

2) 監査ログ DB を初期化する（監査専用 DB を別ファイルで作る例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンに設定されます
```

3) 日次 ETL を実行する（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は market calendar → prices → financials → 品質チェック の順で実行します。
- ID トークンは settings.jquants_refresh_token を使って自動取得／キャッシュされます。

4) ニューススコアの算出（OpenAI を使う）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を利用
print("書込銘柄数:", n_written)
```
- raw_news / news_symbols テーブルが適切に準備されていることが前提です。
- スコアは ai_scores テーブルへ DELETE → INSERT により冪等的に書き込まれます。

5) 市場レジームをスコアリング
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
# market_regime テーブルに regime_score, regime_label が保存されます
```
- 内部で ETF 1321 の ma200_ratio を計算し、マクロニュースの LLM センチメントと合成します。
- OpenAI API キーを None にした場合、環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError。

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

date0 = date(2026, 3, 20)
momentum = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
value = calc_value(conn, date0)
```

7) データ品質チェック（単体）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意: 上記の多くの関数は前提となるテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar 等）が存在することを想定しています。スキーマ作成や初期化はプロジェクト内の別スクリプト／マイグレーションで行う想定です（audit は init_audit_db で自動作成可能）。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 自動ロード / settings
  - ai/
    - __init__.py                — score_news を公開
    - news_nlp.py                — ニュース NLP（銘柄ごとの ai_score）
    - regime_detector.py         — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py     — マーケットカレンダー管理, is_trading_day, next/prev_trading_day 等
    - pipeline.py                — ETL パイプライン / run_daily_etl 等
    - etl.py                     — ETLResult 再エクスポート
    - jquants_client.py          — J-Quants API クライアント（fetch / save / auth / rate limiter）
    - news_collector.py          — RSS からのニュース収集、SSRF 対策、前処理
    - quality.py                 — データ品質チェック（欠損/重複/スパイク/日付不整合）
    - stats.py                   — zscore_normalize 等汎用統計
    - audit.py                   — 監査ログ（signal_events, order_requests, executions）の DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value の計算
    - feature_exploration.py     — forward returns / IC / factor summary / rank

（実際のリポジトリには上記以外のモジュールや補助ファイルがある場合があります）

---

## 知っておくべき注意点 / トラブルシューティング

- 必須環境変数が未設定だと settings の該当プロパティ呼び出しで ValueError が発生します。README の「必須環境変数」を確認してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。CI やテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants API 呼び出しは外部サービス依存のため、API 失敗時はフェイルセーフ（0.0 で継続、またはスキップ）する設計の箇所がありますが、キー未設定は例外になります。
- DuckDB に対するテーブル作成（raw_prices など）は本リポジトリにスキーマ定義スクリプトがある場合はそれを実行してください。audit 用のテーブルは init_audit_db で作成できますが、raw_* 系のスキーマは ETL の前に準備が必要です。
- news_collector は SSRF 対策とレスポンスサイズ制限を含む堅牢な実装を目指していますが、外部 RSS ソースの差異（エンコーディング・日付フォーマット）によりパース警告が発生することがあります。

---

必要に応じて README を拡張して、データベーススキーマ定義、具体的な .env.example、CI 実行手順、ユニットテスト方法などを追加できます。追加で記載したい項目があれば教えてください。