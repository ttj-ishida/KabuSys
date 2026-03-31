# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

主な設計方針：
- DuckDB をデータ格納に利用（軽量で高速な分析向け組み込み DB）
- J-Quants / OpenAI 等外部 API 呼び出しはリトライ・レート制御付きで安全に実施
- ETL / スコアリング処理はルックアヘッドバイアスを避ける設計（date.today() を直接参照しない等）
- DB 書き込みは可能な限り冪等（ON CONFLICT / トランザクション）で実装

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数（.env）例
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

プロジェクト概要
- KabuSys は日本株のデータ ETL、ニュースセンチメント解析、ファクタ研究、監査ログ、監視・発注連携等を行うためのライブラリ群です。
- DuckDB を中心としたローカル DB にデータを蓄積し、研究・バックテスト・実運用の各レイヤーで利用できるモジュールを提供します。

機能一覧
- Data（kabusys.data）
  - J-Quants API クライアント（fetch / save / id_token 管理・レート制御・リトライ）
  - ETL パイプライン（run_daily_etl：カレンダー→株価→財務→品質チェック）
  - カレンダー管理（営業日判定 / next/prev_trading_day / calendar update job）
  - ニュース収集（RSS の安全取得・正規化・raw_news への保存）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログスキーマ初期化・監査 DB（signal / order_request / executions）
  - ユーティリティ（統計関数 zscore_normalize 等）
- AI（kabusys.ai）
  - ニュースの銘柄ごとセンチメント付与（score_news。OpenAI を用いる）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM センチメントを合成、score_regime）
  - OpenAI 呼び出しは JSON-mode を使い、リトライ/フェイルセーフの設計
- Research（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等
- 設定管理（kabusys.config）
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と Settings インターフェース

セットアップ手順（最小構成）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトで使用する追加パッケージがある場合は requirements.txt を用意している想定です。

3. リポジトリをインストール（開発モード）
   - pip install -e .

4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数（必須 / 推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で利用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

.env の例（.env.example 参照）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（サンプルコード）
- DuckDB 接続を作り ETL を実行する（run_daily_etl）

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（OpenAI API キーが必要）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
print(f"wrote {num_written} ai_scores")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB を初期化（監査専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って signal_events / order_requests / executions の操作が可能
```

- 設定の自動ロードを無効化（テストなど）

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージエクスポート)
  - config.py (環境変数・Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント取得・score_news)
    - regime_detector.py (市場レジーム判定・score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch/save 等)
    - pipeline.py (ETL のメイン: run_daily_etl, run_prices_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - calendar_management.py (市場カレンダー・営業日判定)
    - news_collector.py (RSS 収集・正規化)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize 等ユーティリティ)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (momentum / value / volatility)
    - feature_exploration.py (forward returns, IC, factor summary)
  - ai/、research/、data/ 以下に詳細なモジュール実装あり

注意事項 / 設計上のポイント
- ルックアヘッドバイアスの防止
  - 多くの関数が内部で date.today() を直接参照せず、target_date を引数で受け取ります。バックテストや研究での誤った情報流入を防ぎます。
- 冪等性
  - J-Quants から取得したデータの保存は ON CONFLICT DO UPDATE により冪等に実装されています。
- レート制御 / リトライ
  - J-Quants API は固定間隔レートリミッタを利用（120 req/min 相当）。OpenAI 呼び出しもリトライや 5xx/429 の取り扱いが実装されています。
- セキュリティ
  - RSS 取得は SSRF 対策、受信サイズ上限、defusedxml による XML 安全化などの対策を実装しています。
- テスト/モックしやすい設計
  - OpenAI 呼び出しなどは内部関数をパッチしてテスト可能なように分離されています。
- DuckDB バージョン依存
  - 一部実装は DuckDB の executemany / リストバインドに注意して実装されています（空パラメータを避ける等）。

ライセンス / コントリビューション
- 本リポジトリのライセンス表記やコントリビューションガイドはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（本コードベースには含まれていないため、実装に合わせて追記してください）。

---

起動や運用で不明点があれば、どの機能をどう使いたいか（例: ETL 日次バッチを Cron で回したい、OpenAI 呼び出しの課金最適化をしたい 等）を教えてください。具体的な運用例や Docker 化、systemd / Airflow 連携などのサンプルも提供できます。