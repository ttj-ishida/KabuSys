# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼研究・自動売買支援ライブラリです。J-Quants API からの ETL、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および市場レジーム判定等の機能を提供します。

主な想定用途
- データ収集（株価・財務・カレンダー）
- ニュースの収集・LLM によるセンチメント評価
- ファクター計算・研究用統計解析
- ETL バッチ（差分更新）と品質チェック
- 監査ログ（シグナル → 発注 → 約定の追跡）
- 市場レジーム判定（MA とマクロニュースの合成）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（基本的な例）
- 環境変数（.env 例）
- ディレクトリ構成

---

プロジェクト概要
- 言語: Python
- 主な依存: duckdb, openai, defusedxml（ネットワーク/API は標準 urllib を使用）
- 設計方針:
  - ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない設計）
  - ETL / 保存は冪等（ON CONFLICT / UPSERT）を意識
  - API 呼び出しはリトライ・バックオフ・レート制御を備える
  - DB は主に DuckDB を想定（監査用 DB を分けて初期化可能）

---

機能一覧（モジュール別ハイライト）
- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API 取得 / 保存（差分取得、ページネーション、トークン自動リフレッシュ、保存は冪等）
  - pipeline: 日次 ETL 実行 (run_daily_etl)、個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 収集、安全対策（SSRF 対策・受信サイズ制限）と raw_news 保存
  - stats: zscore_normalize 等汎用統計ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログ（signal_events, order_requests, executions）のスキーマ作成・初期化
- kabusys.ai
  - news_nlp.score_news: 記事群を LLM（gpt-4o-mini）で銘柄別センチメント化し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime を更新
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（研究用解析）

---

セットアップ手順（開発環境）
前提
- Python 3.10+（PEP 604 の | 型表記などを利用）
- Git（プロジェクトルート認識のため）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell 等)

3. 依存インストール
   pip install -U pip
   pip install duckdb openai defusedxml

   ※プロジェクト配布で requirements.txt や pyproject.toml があればそちらを使用してください。

4. パッケージを開発モードでインストール（任意）
   pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動的に読み込まれます（自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須項目や推奨項目は次節参照。

---

使い方（基本的なコード例）

1) 設定参照
- settings オブジェクトから環境変数を参照できます。

from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)

2) DuckDB 接続を作って ETL を実行する

import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニューススコアリング（OpenAI API キーが必要）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")

4) 市場レジーム判定（OpenAI API キーが必要）

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

5) 監査ログ DB 初期化（監査専用 DB を作る）

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests/ signal_events 等の操作や検索が可能

注意点
- OpenAI を利用する関数は api_key 引数を受け取りますが、環境変数 OPENAI_API_KEY をセットしておくことが簡単です。
- J-Quants API を使う処理は settings.jquants_refresh_token を参照します。トークンの管理に注意してください。

---

主要な環境変数 (.env 例)
以下は最低限の例です（実プロジェクトでは secret 値は安全に管理してください）。

# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # オプション（デフォルトはこの値）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
KABUSYS_ENV=development
LOG_LEVEL=INFO

必須（モジュールにより異なる）
- JQUANTS_REFRESH_TOKEN: J-Quants API を使う ETL に必須
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合に必須
- KABU_API_PASSWORD: kabu ステーション API を使う場合に必須
- OPENAI_API_KEY: kabusys.ai のスコアリング機能を使う場合に必須

補足
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージ起動時の .env 自動取り込みを無効化できます（テスト用途など）。
- LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py             # ニュース NLP スコアリング（score_news）
    - regime_detector.py      # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + 保存関数
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                  # ETL の公開型再エクスポート（ETLResult）
    - news_collector.py       # RSS 収集と raw_news 保存
    - calendar_management.py  # マーケットカレンダー管理・営業日ロジック
    - stats.py                # zscore_normalize 等汎用統計
    - quality.py              # 品質チェック群
    - audit.py                # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      # モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py  # 将来リターン / IC / 統計サマリー
  - research/*.py
  - その他（strategy, execution, monitoring 等は __all__ に配列済み／将来拡張想定）

（上記はソースツリーの主要ファイルのみ抜粋）

---

運用上の注意
- DuckDB ファイル（settings.duckdb_path）は運用環境のバックアップ・耐障害管理を検討してください。
- OpenAI / J-Quants / 証券 API のレート制限や課金に注意して運用してください。
- 自動売買に移行する前に監査ログ・テスト環境（paper_trading）で十分に検証してください（settings.env により is_paper/is_live が判定されます）。

---

サポート / 貢献
- バグ修正や改善提案は PR を送ってください。大きな設計変更は事前に issue で議論をお願いします。

---

以上。README の内容をプロジェクト方針や運用ルールに合わせて適宜調整してください。必要であれば、各機能の CLI 実装例やユニットテストの書き方、より詳細な .env.example を追記できます。