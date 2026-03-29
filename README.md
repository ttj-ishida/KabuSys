# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレーサビリティ）などを提供します。

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得して DuckDB に保存（ページネーション・レート制御・リトライ対応）。
  - 日次 ETL パイプライン（run_daily_etl）があり、カレンダー取得 → 株価取得 → 財務取得 → 品質チェックを自動実行。
- データ品質管理
  - 欠損、重複、スパイク、日付不整合の検出（quality モジュール）。
- ニュース収集と NLP
  - RSS からニュース記事を収集（SSRF 対策、トラッキング除去、前処理）。
  - OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄ごとのニュースセンチメント解析（news_nlp）。
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次のレジーム判定（bull/neutral/bear）。
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義・初期化を提供。発注フローのトレーサビリティを保証。
- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）や将来リターン計算、IC（Information Coefficient）計算、統計サマリーなどを提供。
- ユーティリティ
  - 統計ユーティリティ（zscore 正規化）、市場カレンダー管理（営業日判定・前後営業日の取得）など。

---

## 必要な環境・依存

- Python 3.10+
- 主要依存（代表例、プロジェクトの pyproject/requirements を参照してください）:
  - duckdb
  - openai (OpenAI の Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- DuckDB（ファイルベースまたはインメモリで使用）

---

## 環境変数（主要）

このライブラリは環境変数を通じて機密情報や設定を読み込みます。`.env` / `.env.local` をプロジェクトルートに置くと自動ロードされます（自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（Settings クラスで require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注関連を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他（省略可、デフォルトあり）:
- KABUSYS_ENV — デプロイ環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール呼び出しで使用）

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .            # 開発用（pyproject/setup があることを前提）
   - あるいは requirements.txt があれば: pip install -r requirements.txt

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定してください。
   - 自動ロードを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベースの親ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 基本的な使い方（例）

以下は代表的な API の呼び出し例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続の準備と日次 ETL 実行
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # 引数 target_date を指定可能
print(result.to_dict())
```

- ニュースセンチメントスコアの取得（OpenAI が必要）
```
from datetime import date
from kabusys.config import settings
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # 指定日のニュースを解析して ai_scores に保存
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定（OpenAI を使用）
```
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
normalized = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降は order_requests / executions 等のテーブルが使えます
```

- RSS 取得（ニュースコレクタ）
```
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 注意事項 / 設計方針の要点

- ルックアヘッドバイアス防止:
  - 多くの関数が内部で `date.today()` や `datetime.today()` を直接参照しない設計です。解析やバックテストで使用する場合は明示的に target_date を渡してください。
- 冪等性:
  - ETL / 保存関数は基本的に冪等（ON CONFLICT / upsert）で実装されています。
- フェイルセーフ:
  - AI API 失敗時はゼロスコア等でフォールバックし、処理を継続する設計（致命的な失敗を避ける）。
- セキュリティ:
  - RSS 取得では SSRF 対策、XML パーサは defusedxml を使用し、受信サイズの上限を設けるなど安全対策あり。
- ローカル環境と本番の切替:
  - KABUSYS_ENV による環境区別（development / paper_trading / live）を提供。発注系を本番で使う際は十分な検証を行ってください。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み・Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM 合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - quality.py — データ品質チェック
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py — RSS 収集・前処理
    - audit.py — 監査ログスキーマ初期化（signal / order / execution）
    - stats.py — 統計ユーティリティ（zscore_normalize 等）
    - etl.py — ETLResult エクスポートラッパ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - ai/, data/, research/ それぞれにビジネスロジック・ユーティリティを分離

（上記は主なモジュールです。詳細はソースコードを参照してください）

---

## よくある用途フロー（例）

1. 環境変数をセットして ETL を実行（run_daily_etl）。
2. news_collector によって raw_news を更新（あるいは外部プロセス）。
3. AI モジュールで ai_scores を更新（score_news）。
4. research モジュールでファクターを計算・正規化して信号生成（独自実装のストラテジー層へ）。
5. 監査テーブルに signal → order_request → executions のトレースを残しながら約定処理を行う。

---

## 貢献・拡張

- 新しい RSS ソースの追加、AI プロンプト調整、ファクターの追加はモジュール単位で拡張可能です。
- テスト時は環境自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、関数内で環境変数を差し替えるかモックしてください。
- OpenAI / J-Quants の呼び出し部分はリトライやバックオフを実装済みですが、本番運用ではレートやコストに注意して運用してください。

---

README や API ドキュメントに追記したい内容（例: 詳細な .env.example、CLI ラッパー、ユニットテスト手順等）があれば教えてください。必要に応じてサンプル .env.example や具体的な運用手順（cron / Airflow / GitHub Actions など）も作成します。