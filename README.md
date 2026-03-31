# KabuSys

日本株自動売買プラットフォーム用のコアライブラリ群。データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーなどのデータ取得（差分取得・ページネーション対応）
- DuckDB を用いた ETL パイプラインと品質チェック
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント（銘柄ごとの ai_score）算出
- ETF ベースの移動平均とニュースセンチメントを合成した市場レジーム判定
- リサーチ用ファクター計算と統計ユーティリティ
- 発注／約定に関する監査ログスキーマの初期化ユーティリティ

設計上の特徴として、ルックアヘッドバイアス回避（target_date を明示的に扱う）、再現性のための fetched_at 管理、冪等保存（ON CONFLICT / upsert）などが組み込まれています。

---

## 主な機能一覧

- data（J-Quants クライアント・ETL）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェックの一括実行
  - calendar 関連ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - news_collector：RSS 収集・前処理（SSRF 対策・トラッキング除去等）
  - quality：欠損・スパイク・重複・日付不整合チェック
  - audit：監査ログ（signal_events / order_requests / executions）スキーマ初期化

- ai
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores テーブルへ保存
  - regime_detector.score_regime：ETF（1321）200日MA乖離とニュースセンチメントを合成し market_regime に書き込み

- research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize（クロスセクション Z スコア正規化）

- 設定管理
  - config.Settings：環境変数・.env の自動ロード（プロジェクトルート検出）と必須チェック

---

## セットアップ手順

前提
- Python 3.9+（typing 機能を多用しているため）
- DuckDB を利用（pip install duckdb）
- OpenAI SDK（pip install openai）
- defusedxml（RSS 安全処理）
- その他標準ライブラリ以外の依存パッケージに注意

推奨インストール例（プロジェクトルートで）:

```bash
# 仮想環境を作成・有効化
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate.bat  # Windows

pip install -U pip
pip install duckdb openai defusedxml
# 他に必要なパッケージがあれば追加してください
# 例: pip install pytest
```

プロジェクトを editable インストール（開発用）:

```bash
pip install -e .
```

環境変数 (.env)
- プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
- 必須キー（モジュール利用時に参照されます）:
  - JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン
  - KABU_API_PASSWORD - kabu ステーション API パスワード（必要な場合）
  - SLACK_BOT_TOKEN - Slack 通知用（必要な場合）
  - SLACK_CHANNEL_ID - Slack チャネル ID
  - OPENAI_API_KEY - OpenAI を利用する場合（news_nlp / regime_detector）
- 任意（デフォルト値あり）:
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development | paper_trading | live) default: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) default: INFO

.env 例（.env.example を参照して作成）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

セキュリティ:
- API鍵・トークンは絶対に公開リポジトリへ置かないでください。
- 本ライブラリは自動で .env を読み込むため、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を使って制御できます。

---

## 使い方（簡易ガイド）

以下は主要ユースケースの最小例です。詳細は関数ドキュメント（docstring）を参照してください。

1) DuckDB 接続を作成して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（OpenAI を使って銘柄別スコア算出）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（regime_detector）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへアクセス可能
```

5) リサーチ関数の利用例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- AI 呼び出し（OpenAI）は外部 API へ依存するため API キーと通信環境が必要です。API 呼び出しはリトライ・フェイルセーフを備えていますが、料金やレート制限には注意してください。
- ETL / データ取得は J-Quants API のレート制限を考慮して実行してください。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要ファイル・モジュールの一覧と簡単な説明です。

- kabusys/
  - __init__.py              - パッケージ初期化、__version__
  - config.py                - 環境変数 / .env 読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py            - ニュースの LLM によるセンチメント算出（ai_scores への書き込み）
    - regime_detector.py     - ETF MA とニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（fetch/save の実装）
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - etl.py                 - ETLResult 再エクスポート
    - news_collector.py      - RSS 収集・前処理（SSRF 対策等）
    - quality.py             - データ品質チェック（欠損・スパイク等）
    - calendar_management.py - 市場カレンダー管理（is_trading_day 等）
    - audit.py               - 監査ログスキーマ初期化（signal/order/execution）
    - stats.py               - 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py     - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py - 将来リターン・IC・統計サマリー等
  - monitoring/               - （監視用モジュール等：コードベースに応じて追加）
  - strategy/                 - （戦略実装用のフレームワーク：本リポジトリ内に展開）

（注）ここに挙げた各モジュールは docstring で詳細が記載されています。実運用で利用する際は docstring をよく読み、環境変数や DB スキーマが適切に準備されていることを確認してください。

---

## 開発・運用上の注意

- ルックアヘッドバイアス回避: 多くの関数は内部で datetime.today()/date.today() を参照せず、外部から target_date を受け取る設計です。バックテストや再現性のため必ず target_date を明示的に渡すか、挙動を理解して使用してください。
- 冪等性とトランザクション管理: 多くの保存処理は ON CONFLICT（upsert）を利用していますが、複数操作を原子的に行う場合は明示的に BEGIN/COMMIT を使用してください（DuckDB のトランザクション制限に注意）。
- テスト: API 呼び出し部分（OpenAI / J-Quants / RSS）の関数はモックしやすいように設計されています。ユニットテストではモックを使って外部通信を差し替えてください。
- セキュリティ: news_collector は SSRF を防ぐ検査、defusedxml による XML パース保護、応答サイズ制限などを実装しています。外部 URL を扱う際はログや例外を監視してください。

---

何か特定の利用例（ETL の自動化、CI でのテスト、OpenAI のレスポンスバリデーションなど）に関する README の追記や、実行スクリプト例が必要であれば教えてください。詳細なコマンドや設定テンプレートを用意します。