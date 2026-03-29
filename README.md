# KabuSys — 日本株自動売買 / データプラットフォーム

KabuSys は日本株向けのデータパイプライン、リサーチ、ニュース NLP、ならびに監査（オーディット）や市場レジーム判定を含む自動売買プラットフォームのライブラリ群です。本リポジトリは主に以下の役割を持つモジュール群で構成されています。

- データ取り込み ETL（J-Quants 経由の株価・財務・カレンダー）
- ニュース収集 & LLM によるニュースセンチメント評価
- 市場レジーム判定（MA + マクロニュースの組合せ）
- リサーチ用ファクター計算・特徴量解析
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック、マーケットカレンダー管理

README ではプロジェクトの概要、機能、セットアップ手順、使い方（主要 API の利用例）、およびディレクトリ構成を日本語でまとめます。

---

## 主な機能

- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API から差分取得し DuckDB に冪等保存
  - カレンダーのバックフィル・先読み対応、品質チェック連携
- ニュース関連
  - RSS フィード収集（安全対策：SSRF/プライベートIP の検査、サイズ制限、XML 脆弱性対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定（score_regime）
  - ETF（1321）の200日移動平均乖離 + マクロニュースセンチメントを統合して日次レジームを判定
- リサーチ（research モジュール）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック（quality モジュール）
  - 欠損、スパイク、重複、日付不整合検知
- 監査ログ（audit モジュール）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
- 設定管理（config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須変数チェック、環境切替（development/paper_trading/live）等

---

## 要件（概略）

- Python 3.10+
- 主要依存ライブラリ（抜粋）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- 標準ライブラリのみで実装されているユーティリティも多く、追加の依存は個別機能に応じて必要になります。

（プロジェクト配下に pyproject.toml や requirements.txt がある場合はそちらを優先してください。）

---

## インストール（開発環境）

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージを編集可能モードでインストール
   - pip install -e .

3. 追加依存のインストール（例）
   - pip install duckdb openai defusedxml

※ 実行環境によりさらに依存関係が必要となる場合があります。CI / packaging 設定があればそれに従ってください。

---

## 設定（環境変数・.env）

config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（プロジェクトに合わせて .env を作成してください）:

- JQUANTS_REFRESH_TOKEN  
  - J-Quants 用のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD  
  - kabuステーション API 用のパスワード（発注等）
- SLACK_BOT_TOKEN  
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID  
  - Slack チャンネル ID
- OPENAI_API_KEY  
  - OpenAI を使う機能（news_nlp, regime_detector）で利用

その他（任意・デフォルトあり）:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動ロードを無効化

.env のサンプル（プロジェクトに .env.example があればそれを参考に）:

```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API と例）

以下は各主要機能の利用例です。各関数は「target_date」を明示的に受け取り、内部で datetime.today() を参照しない実装方針（ルックアヘッドバイアス対策）になっています。バックテストや再現性のために target_date を明示してください。

環境に応じて duckdb をインストールしてください。

1) DuckDB 接続の例

```python
import duckdb
conn = duckdb.connect('data/kabusys.duckdb')
```

2) 日次 ETL 実行（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 25))
print(result.to_dict())
```

3) ニュースセンチメントのスコア算出（score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 25))
print(f"scored {num_written} symbols")
```

4) 市場レジーム判定（score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 25))
```

5) リサーチ用ファクター計算（例：モメンタム）

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 25))
# records は各銘柄ごとの dict リスト（date, code, mom_1m, mom_3m, ...）
```

6) 統計正規化ユーティリティ

```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
```

7) 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへ書き込み/クエリを実行できます
```

8) RSS フィード取得（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 返り値は NewsArticle 型のリスト（id, datetime, source, title, content, url）
```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク/料金が発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api 等を差し替えることを想定しています。
- score_news / score_regime は API キーが必須（引数で渡すか OPENAI_API_KEY 環境変数）です。未設定時は ValueError を送出します。
- ETL および保存処理は冪等性を考慮して実装されています（ON CONFLICT / DELETE→INSERT パターン）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py (パッケージ化、version)
  - config.py (環境変数 / .env 自動読み込み / settings)
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py (ニュースセンチメントスコア化、score_news)
    - regime_detector.py (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch/save 等)
    - pipeline.py (ETL パイプライン、run_daily_etl 他、ETLResult)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集、安全対策)
    - calendar_management.py (market_calendar 管理、is_trading_day 等)
    - stats.py (zscore_normalize 等)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ定義・初期化)
  - research/
    - __init__.py (研究用ユーティリティのエクスポート)
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - ai/ (上記に含む)
  - research/ (上記に含む)

各モジュールはドキュメント文字列（docstring）で設計方針や処理フローが詳細に記述されています。実装の振る舞い（例：API リトライ方針、ロギング、フェイルセーフ動作）は各ファイル先頭のコメントにまとめられています。

---

## 開発・テストに関する補足

- 自動環境変数ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込みます。OS 環境変数は保護され上書きされません。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。
- ルックアヘッドバイアス対策:
  - news_nlp, regime_detector, ETL, research 等の関数は target_date を取る設計です。内部で `datetime.today()` や `date.today()` を参照せず、バックテストでの再現性を保つように実装されています。
- テスト:
  - OpenAI 呼び出しや外部 API 呼び出しはモックが容易になる設計（内部の _call_openai_api を patch する等）になっています。

---

## おわりに

この README はコードベースの主要な機能と使い方をまとめたものです。各モジュールには詳細な docstring があり、内部の設計方針や例外ハンドリング、リトライ・フェイルセーフ処理などが記述されています。利用／拡張する際は該当ファイルの docstring を参照してください。

追加で README に含めたい内容（インストールの正確な依存リスト、実行スクリプト、CI 設定、.env.example の内容など）があれば教えてください。README をそれに合わせて拡張します。