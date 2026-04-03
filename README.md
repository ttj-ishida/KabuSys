# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ収集）、ニュースセンチメント解析（OpenAI を利用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）の初期化・管理などを提供します。

---

## 特徴（機能一覧）

- データ収集・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーをページネーション対応で差分取得
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- ニュース／AI
  - RSS 収集器（SSRF対策、URL 正規化、前処理）と raw_news テーブルへの保存
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄ごと）スコアリング（score_news）
  - マクロニュース + ETF（1321）200日移動平均乖離を合成した市場レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化など

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（未来日や非営業日のデータ）チェック（quality.run_all_checks）

- カレンダー管理
  - market_calendar 用の差分取得・更新ジョブ（calendar_update_job）
  - 営業日判定、前後営業日取得、期間内の営業日取得

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブルを初期化（init_audit_schema / init_audit_db）
  - 発注フローの UUID ベース追跡をサポート

---

## セットアップ

前提
- Python 3.9+（typing の某種機能や型ヒントのため）を想定しています（実際の最小要件はプロジェクト方針に従ってください）。
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - openai もしくは OpenAI Python SDK（コードは OpenAI クライアント呼び出しを想定）
  - defusedxml

例: pip を使った最小インストール例
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他プロジェクト独自の依存があれば requirements.txt があればそれを使用してください
# pip install -r requirements.txt
```

環境変数
- 本プロジェクトは .env / .env.local から自動で環境変数を読み込みます（プロジェクトルートに .git または pyproject.toml が存在する場合）。
- 自動読み込みを無効にするには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主要な設定キー（Settings プロパティに対応）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API リフレッシュトークン
- OPENAI_API_KEY（score_news / score_regime のデフォルト）
- KABU_API_PASSWORD（kabuステーション API 用）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB, デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視の閾値）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 .env（必須項目だけ抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=your_openai_api_key_here
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
LOG_LEVEL=DEBUG
KABUSYS_ENV=development
```

注意:
- settings.jquants_refresh_token は必須です。未設定時は ValueError が発生します。
- OPENAI_API_KEY は score_news / score_regime の呼び出し時に引数として渡すこともできます。

---

## 使い方（主要な API と実行例）

以下は Python スクリプト / REPL から直接呼び出す形の簡単な例です。DuckDB の接続には duckdb.connect() を使用します。

1) 日次 ETL 実行（J-Quants からデータ取得 -> DuckDB に保存 -> 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース（AI）スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
print("書き込んだ銘柄数:", written)
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
```

4) 監査ログスキーマ初期化（別 DB に監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb.DuckDBPyConnection
```

5) ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

6) データ品質チェック実行
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

各関数はドキュメント文字列（docstring）で引数・戻り値の意味が詳述されています。API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用します。

---

## ディレクトリ構成

以下は主要なファイル／モジュール一覧（コードベースの抜粋に基づく）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  -- 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py              -- ニュースセンチメント（score_news）
      - regime_detector.py       -- マクロ + MA200 を使ったレジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py        -- J-Quants API クライアント（fetch/save）
      - pipeline.py              -- ETL パイプライン（run_daily_etl 他）
      - etl.py                   -- ETLResult の再エクスポート
      - calendar_management.py   -- 市場カレンダー管理（is_trading_day 等）
      - news_collector.py        -- RSS 収集・前処理
      - stats.py                 -- 共通統計ユーティリティ（zscore_normalize）
      - quality.py               -- データ品質チェック
      - audit.py                 -- 監査ログスキーマ初期化（init_audit_schema/init_audit_db）
    - research/
      - __init__.py
      - factor_research.py       -- ファクター計算
      - feature_exploration.py   -- 将来リターン / IC / 要約等
    - ai, data, research パッケージの下にさらに補助関数や定数が含まれます

この README は提供済みコードの主要モジュールに基づく要約です。詳細な API（各関数の引数/返り値/例外）については、各モジュールのドキュメント文字列を参照してください。

---

## 運用上の注意・設計方針（抜粋）

- ルックアヘッドバイアス対策:
  - 各処理は内部で date.today() を直接参照しない姿勢が採られており、target_date を明示的に渡して使用する設計です。バックテスト時は必ず過去のみ参照するよう注意してください。

- フェイルセーフ:
  - OpenAI や外部 API の失敗時、致命的に停止させずフォールバック（例: macro_sentiment=0）して継続する実装が多いです。必要に応じてログを監視してください。

- 冪等性:
  - DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して作られています。ETL はバックフィル戦略を備えています。

- セキュリティ:
  - RSS 収集では SSRF 対策（リダイレクト先検査、private address 判定）を実施。
  - XML パースは defusedxml を使用。

---

もし具体的に README に追加したいサンプルや CI / テストの手順、あるいはパッケージ公開向けの setup・pyproject のテンプレートが必要であれば教えてください。README をその用途に合わせて拡張します。