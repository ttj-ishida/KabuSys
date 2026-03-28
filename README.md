# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
DuckDB を用いたデータ ETL、データ品質チェック、ニュース NLP（OpenAI を用いたセンチメント解析）、市場レジーム判定、ファクター計算、監査ログ（発注／約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存（ETL）
- ニュース記事の収集と銘柄ごとの NLP センチメント評価（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントの合成）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と探索的解析（IC, forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査 / トレーサビリティ（signal → order_request → execution を追跡する監査テーブル）
- kabuステーション API / Slack 等の設定管理（環境変数ベース）

設計方針の一部：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- 冪等性を重視（DB 保存は ON CONFLICT などで上書き）
- 外部 API 呼び出しはリトライ・バックオフを実装しフェイルセーフ（失敗時に処理継続）  

---

## 機能一覧

- data
  - ETL: 差分取得・保存（prices / financials / market calendar）
  - calendar_management: 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
  - jquants_client: J-Quants API クライアント（認証、ページネーション、保存関数）
  - news_collector: RSS からニュース収集（SSRF 対策、URL 正規化、前処理）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: 汎用統計ユーティリティ（z-score）
  - audit: 監査ログテーブルの初期化・管理（signal_events, order_requests, executions）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントの生成と ai_scores への書込み（OpenAI）
  - regime_detector.score_regime: 市場レジーム（bull/neutral/bear）判定と market_regime への書込み（OpenAI + ETF MA）
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数読み込み・設定管理（.env 自動読み込み、required 環境変数の検査）

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントで | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（最低限の依存のみ）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

プロジェクト配布形式に応じて、requirements.txt / pyproject.toml からインストールしてください。

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数（config.Settings 参照）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (省略時: data/kabusys.duckdb)
  - SQLITE_PATH (省略時: data/monitoring.db)
- システム設定
  - KABUSYS_ENV (development / paper_trading / live) デフォルト: development
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO
- OpenAI
  - OPENAI_API_KEY (ai.score_news / regime_detector で使用可能、関数呼び出し時に api_key 引数で上書き可)

.env の例（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを設置
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存をインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   ```
   ※ プロジェクトに requirements があればそれを使用してください。
4. `.env` をプロジェクトルートに作成し、必要な環境変数を設定
5. DuckDB ファイルの親ディレクトリ（例: data/）を作成しておく（多くの関数が自動で作成します）

---

## 初期化 / データベース準備

監査ログ専用の DuckDB を初期化する例:

```python
from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# ファイルパスを指定して監査DBを作成・接続
audit_db_path = Path(settings.duckdb_path)  # 例: data/kabusys.duckdb
conn = init_audit_db(audit_db_path)  # トランザクション内でスキーマ作成
# conn を用いてさらに初期化処理が可能
conn.close()
```

既存接続にスキーマだけ追加したい場合は `init_audit_schema(conn, transactional=True)` を使用します。

---

## 主要な使い方（サンプル）

- 日次 ETL を実行してデータを DuckDB に取り込む:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースの NLP スコアを生成して ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されている前提
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
conn.close()
```

- 市場レジームを判定して market_regime に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- 研究系ユーティリティの例（モメンタム算出）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records), "records")
conn.close()
```

注意点:
- OpenAI を用いる関数は API キーが必要です（引数で渡すか OPENAI_API_KEY を設定）。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar 等）が前提です。スキーマ初期化機能はプロジェクト外にある場合もあるので、最初に schema を準備する必要があります（本リポジトリ内にスキーマ初期化ユーティリティがない場合は手動で CREATE TABLE が必要）。

---

## 製品ディレクトリ構成（概観）

プロジェクトの主要ファイル・パッケージ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター・探索系ユーティリティ）
  - その他（strategy / execution / monitoring 等のプレースホルダが __all__ に記載）

各モジュールの責務:
- config.py: 環境変数の読み込み・検証（.env 自動読み込みロジック含む）
- data/jquants_client.py: J-Quants API 呼び出し・保存ロジック（レートリミット・リトライ・認証）
- data/pipeline.py: ETL の統合エントリポイント（run_daily_etl など）
- data/quality.py: ETL 後のデータ品質チェック
- ai/news_nlp.py: ニュースを銘柄毎に集約して LLM へ送り、ai_scores に保存
- ai/regime_detector.py: MA と LLM を組み合わせた市場レジーム判定
- research/*: ファクター計算・IC 等の解析ユーティリティ
- data/audit.py: 監査（signal / order_request / execution）テーブル定義と初期化

---

## 注意事項 / 運用メモ

- 自動読み込みされる `.env` はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に検索します。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API 使用料とレート制限に留意してください。
- jquants_client は API レート（120 req/min）を尊重するよう実装されていますが、長時間のページネーションやバッチ処理を行う際は運用上の配慮が必要です。
- DuckDB のバージョン依存（executemany の空リスト不可など）に注意したコードが含まれています。DuckDB の互換性に関する問題があればバージョンを固定してください。
- 本ライブラリはバックテスト・実取引の両方に使われうる機能を含みます。実運用（live）モードでは特に安全性（ダブル発注防止、監査ログの完全性、order_request の冪等性）を確認してください。

---

## 参考 / 連絡

実装や利用方法に関する疑問点・改善要望があれば、リポジトリの issue に記載してください。README の内容はコードベースのコメント・docstring を元に作成しています。