# KabuSys

バージョン: 0.1.0

日本株向けのデータプラットフォームおよび自動売買支援ライブラリ。J-Quants / OpenAI 等を利用したデータ ETL、ニュース NLP、市場レジーム判定、ファクター計算、監査ログ機能などを提供します。

主な用途:
- J-Quants からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と OpenAI を用いた銘柄別センチメントスコア算出
- ETF ベースの市場レジーム判定（MA200 + マクロニュース）
- 研究用途のファクター計算・IC/forward-return 分析
- DuckDB を用いた監査ログスキーマ初期化と保存

---

## 機能一覧

- 環境設定管理 (.env 自動ロード / 環境変数)
- J-Quants API クライアント
  - 株価日足 (OHLCV)、財務データ、上場情報、JPX マーケットカレンダーの取得
  - レート制限管理・トークン自動リフレッシュ・リトライ実装
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL エントリポイント (run_daily_etl)
- データ品質チェックモジュール
- ニュース収集 (RSS) と前処理（SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア算出と ai_scores テーブルへの保存 (score_news)
  - レスポンスのバリデーションとバッチ処理・リトライ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントの合成 (score_regime)
- 研究用モジュール
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions 等を含む冪等スキーマ初期化 helper
- ユーティリティ（統計、カレンダー管理、監視パス設定等）

---

## 要件 (推奨)

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

必要に応じてプロジェクトの requirements.txt を作成してください。例:
pip install duckdb openai defusedxml

---

## 環境変数

主に以下を使用します（.env で設定可）。プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API が必要な場合のパスワード

任意／デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- OPENAI_API_KEY (score_news / score_regime で使用可能)

設定例(.env):
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順

1. リポジトリをチェックアウト（この README はソースコードベースの README.md 想定）
2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   pip install duckdb openai defusedxml
   ※ requirements.txt があればそれを使ってください。
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - 必須トークン (JQUANTS_REFRESH_TOKEN 等) を設定
5. DuckDB ファイル等のディレクトリを作成（必要なら）
   mkdir -p data

---

## 使い方（主要な例）

以下は Python スクリプトや REPL から呼ぶ想定の例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

1) DuckDB 接続の生成（設定ファイル経由）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP スコアの実行（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込銘柄数: {written}")
```

4) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

6) RSS フィード取得（ニュース収集のユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

---

## 主要な API / エントリポイント一覧

- kabusys.config.settings — 環境設定 accessor
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のメイン
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl — 各 ETL
- kabusys.data.quality.run_all_checks — 品質チェック
- kabusys.data.jquants_client.* — J-Quants API の取得/保存ヘルパー
- kabusys.data.news_collector.fetch_rss — RSS 取得・前処理
- kabusys.ai.news_nlp.score_news — ニュースによる銘柄別 ai_score 計算
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定
- kabusys.research.* — ファクター計算・解析関数群
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査スキーマ初期化

---

## ディレクトリ構成

（リポジトリの src/kabusys 下の主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETL 公開インターフェース（ETLResult）
    - news_collector.py            — RSS 収集 / 前処理
    - calendar_management.py       — マーケットカレンダー管理
    - stats.py                     — 統計ユーティリティ（zscore 等）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility
    - feature_exploration.py       — forward returns / IC / summary
  - ai/ (上記)
  - research/ (上記)
  - その他モジュール（strategy/ execution/ monitoring 等のプレースホルダ）

---

## 注意事項 / 実運用に関するメモ

- OpenAI 呼び出しや外部 API は失敗時にフェイルセーフ（スコア 0 や処理スキップ）となるよう設計されていますが、API キーやレート制限に注意してください。
- DB 書き込みは冪等性を保つよう ON CONFLICT ロジックが入っていますが、運用時はバックアップと権限設定を行ってください。
- ニュース収集では SSRF 対策・受信サイズ制限・XML の安全パーサを利用しています。それでも外部フィードについては信頼できるソースを優先してください。
- テスト時は自動 .env ロードを無効化できます: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Python の型ヒントや設計はバックテスト時の「ルックアヘッドバイアス」を避ける方針で実装されています（target_date を明示する等）。

---

必要であれば README に入れるサンプル .env.example、requirements.txt、簡単な CLI や systemd サービス定義、あるいはデプロイ手順のテンプレートも作成できます。どの情報を優先して追加しますか？