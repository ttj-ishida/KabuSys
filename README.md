# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP（OpenAI を利用したセンチメント付与）、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）
- 使い方（簡単な利用例）
- ディレクトリ構成（主要ファイル解説）
- 注意点 / 設計方針メモ

---

## プロジェクト概要

KabuSys は日本株向けのデータインフラ / 研究 / 自動売買支援ライブラリです。  
主な目的は以下：

- J-Quants API からの差分 ETL（株価日足 / 財務 / マーケットカレンダー）の自動取得・保存
- RSS ベースのニュース収集と記事の前処理（SSRF 対策、トラッキングパラメータ除去等）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 日次の市場レジーム判定（ETF MA と LLM マクロセンチメントの複合）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）を保存する監査スキーマの初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- Look-ahead bias を避ける（target_date ベースの計算、現在時刻参照を極力排除）
- DuckDB をデータストアとして利用
- 冪等性（ON CONFLICT / idempotent な保存）とフェイルセーフ：API 失敗時も継続できる設計
- 外部 API 呼び出しのリトライ、レート制御および安全対策（SSRF / XML 攻撃対策 等）

---

## 主な機能一覧

- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult として返却、品質チェック統合
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save の実装（ページネーション対応、トークン自動リフレッシュ、レート制御）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、記事 ID 生成、前処理、DB への冪等保存（raw_news, news_symbols）
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとのニュースをまとめて LLM に送信し ai_scores を作成
- レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロセンチメントの合成で市場レジームを判定・保存
- リサーチ（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等
  - zscore_normalize（kabusys.data.stats）を含む
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合チェック、QualityIssue によるレポート
- 監査ログ（kabusys.data.audit）
  - 監査スキーマの初期化（init_audit_schema / init_audit_db）、監査テーブル DDL

---

## セットアップ手順

前提：
- Python 3.10+（typing の Union | 記法があるため）
- ネットワーク接続（J-Quants / OpenAI アクセス用）

推奨手順（プロジェクトルートで実行）:

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール  
   必要な主要ライブラリ（例）:
   - duckdb
   - openai
   - defusedxml
   - requests（省略可能。標準 urllib を利用しているため必須ではない）
   - そのほか（標準ライブラリで賄う設計ですが、OpenAI SDK と duckdb は必要）

   例:
   pip install duckdb openai defusedxml

   ※ 実際はプロジェクト配布時に requirements.txt / pyproject.toml を用意してください。
   また開発時は pip install -e .（パッケージを編集可能モードでインストール）を推奨します。

3. 環境変数を設定（.env 推奨）
   - プロジェクトルートに .env を置くと自動的に読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. DuckDB / SQLite 用のデータディレクトリ作成（例）
   mkdir -p data

---

## 環境変数（主要）

KabuSys は環境変数（または .env）から設定を読み込みます。必須項目は以下。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token() で使用。

- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード（発注機能を使う場合）。

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用の Bot トークン（通知機能を使う場合）。

- SLACK_CHANNEL_ID (必須)  
  Slack の投稿先チャンネル ID。

- OPENAI_API_KEY  
  OpenAI 呼び出し時の API キー。score_news / score_regime では引数でも渡せますが、環境変数での設定が一番簡便です。

オプション / デフォルト:

- KABUSYS_ENV (development | paper_trading | live)  
  デフォルト: development

- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)  
  デフォルト: INFO

- KABU_API_BASE_URL  
  デフォルト: http://localhost:18080/kabusapi

- DUCKDB_PATH  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH  
  デフォルト: data/monitoring.db

.env 例（シンプル）:
KEY=VALUE
または
export KEY="VALUE"

注意: .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。

---

## 使い方（簡単な利用例）

以下は典型的な操作例です。各関数の引数や返却値はコードの docstring を参照してください。

1) DuckDB 接続の作成と日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースのセンチメントスコア（銘柄別）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を env に設定済みの場合
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を env に設定済みまたは引数で渡す
```

4) 監査 DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/monitoring.db")
# conn_audit は DuckDB 接続。必要に応じてアプリから order_requests / executions を記録
```

5) カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) リサーチ関数（モメンタム等）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records: list[dict] - 各銘柄の mom_1m/mom_3m/mom_6m/ma200_dev 等
```

---

## ディレクトリ構成（主要モジュール説明）

- src/kabusys/
  - __init__.py: パッケージ初期化（__version__ 等）
  - config.py: 環境変数 / 設定管理（.env 自動読み込み・設定プロパティ）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメントスコア（銘柄別）を生成し ai_scores に保存
    - regime_detector.py: ETF MA とマクロセンチメントを合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API (fetch/save)・認証・レート制御・リトライ
    - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py: ETLResult の再エクスポート
    - news_collector.py: RSS 取得・前処理・SSRF 対策・raw_news への保存
    - calendar_management.py: 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py: データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査テーブル DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py: Momentum / Value / Volatility / Liquidity 等の計算
    - feature_exploration.py: 将来リターン計算 / IC / ランク / 統計サマリー
  - research パッケージは主にバックテスト・特徴量探索用の関数群

その他: 各モジュールに詳細な docstring（関数説明・設計上の注意）が含まれているため、実装の利用前に参照することを推奨します。

---

## 注意点 / 設計メモ

- OpenAI 呼び出し
  - news_nlp と regime_detector は LLM を利用します。API 失敗時は安全側（ゼロスコア/スキップ）にフォールバックする設計です。
  - テスト時は内部の _call_openai_api をモックして検証できる設計になっています。

- Look-ahead bias の回避
  - ほとんどの関数は内部で datetime.today() を直接参照せず、target_date を明示して計算します（バックテスト安全性に配慮）。

- 自動読み込みされる .env のパースは shell 形式（export を含む）や引用符・エスケープに対応した実装になっています。特定の値をテストで上書きしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効化してください。

- DuckDB について
  - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb（settings.duckdb_path）です。適切にディレクトリを作成しておいてください。

- セキュリティ
  - news_collector は SSRF 対策 / コンテンツ長チェック / gz 解凍後のサイズチェックなどを実装しています。RSS ソースは信頼できるもののみを登録してください。

---

必要であれば README に「開発者向けのセットアップ（テスト実行方法、フォーマット / lint 設定、CI 設定）」や「API リファレンス（主要関数の引数/返り値の詳細）」を追記できます。どの情報を補強したいか教えてください。