# KabuSys

日本株向け自動売買／データプラットフォームのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP によるセンチメント評価、ファクター計算・リサーチ、監査ログ（発注/約定トレーサビリティ）、カレンダー管理など、バックテスト／運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要な API 例）
- 環境変数一覧
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を用いた市場データ（株価日足・財務・上場情報・マーケットカレンダー）取得と DuckDB への保存（ETL）。
- RSS ベースのニュース収集と前処理、OpenAI（gpt-4o-mini）によるニュース／マクロセンチメント評価。
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算、将来リターン・IC 計算などのリサーチ機能。
- 監査ログ（signal_events / order_requests / executions）用のスキーマ初期化ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）とマーケットカレンダー管理。
- 環境変数 / .env の自動読み込み（プロジェクトルートを検出）をサポート。

主な機能一覧
- data.jquants_client: J-Quants からの取得、DuckDB への冪等保存（save_... 系）、ページネーション・再試行・レート制限対応
- data.pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL 実行と ETLResult）
- data.quality: 欠損・スパイク・重複・日付整合性チェック（QualityIssue）
- data.news_collector: RSS 取得、前処理、SSRF 対策、記事 ID 正規化
- ai.news_nlp: ニュース記事を銘柄ごとに集約して OpenAI でセンチメント評価（score_news）
- ai.regime_detector: ETF(1321) の MA200 乖離とマクロニュース LLM 結果を合成して市場レジーム判定（score_regime）
- research.*: ファクター計算（calc_momentum / calc_value / calc_volatility）、特徴量解析・IC（calc_forward_returns / calc_ic / factor_summary）
- data.calendar_management: market_calendar を用いた営業日判定・前後営業日取得・カレンダー更新ジョブ
- data.audit: 監査ログ用の DDL/インデックス生成 / init_audit_db（DuckDB 初期化）
- config: .env 自動ロード、設定値（settings）アクセス

---

セットアップ手順（開発環境向け）
1. リポジトリをクローンします。
   - 例: git clone <your-repo-url>

2. 仮想環境を作成して有効化（任意）。
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストールします（プロジェクトに requirements.txt がない場合は最低限以下を入れてください）。
   - pip install duckdb openai defusedxml

   （プロジェクト配布時に setup.py / pyproject.toml を用いる場合は `pip install -e .` を推奨）

4. .env ファイルをプロジェクトルートに作成します（下記「環境変数一覧」を参照）。  
   自動読み込みはデフォルトで有効です。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

5. DuckDB を用いるため、データディレクトリを作成しておくと便利です（デフォルト path: data/kabusys.duckdb）。
   - mkdir -p data

注意: OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。J-Quants 使用部分は JQUANTS_REFRESH_TOKEN を必要とします。

---

環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token に使用。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（発注モジュールで使用）。

- KABU_API_BASE_URL (任意)  
  kabuAPI のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用ボットトークン。

- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  監視用 SQLite のパス。デフォルト: data/monitoring.db

- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT ...  
  監視関連の設定（monitoring モジュールで使用）。

- KABUSYS_ENV (任意)  
  動作環境: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

OpenAI:
- OPENAI_API_KEY（score_news / score_regime は引数で渡すことも可能）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config モジュールによる .env 自動ロードを無効化できます（テスト用途等）。

---

使い方（簡単なコード例）

※ すべての API は DuckDB 接続（duckdb.connect(...) で得られる接続オブジェクト）を受け取ります。

1) DuckDB 接続例
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイル DB に接続（デフォルト path は settings.duckdb_path）
conn = duckdb.connect("data/kabusys.duckdb")

# 監査 DB を別ファイルに初期化する例
audit_conn = init_audit_db("data/audit.duckdb")
```

2) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメント（銘柄別）評価
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```

6) 監査スキーマ初期化（既存 DB に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点（挙動の補足）
- OpenAI 呼び出しはリトライ実装がありますが、最終的に失敗した場合はニューススコアや macro_sentiment は 0.0 にフォールバックし、処理は継続します（フェイルセーフ）。
- 時刻関連（news window / regime 判定等）は Look-ahead bias を避けるため内部で date/target_date ベースの計算を行い、datetime.today() の直接参照を避けています。
- テストでは各モジュールの _call_openai_api 等をモックして動作検証可能です。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・.env 読み込み用設定オブジェクト (settings)
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュース -> 銘柄別センチメントスコア (score_news)
    - regime_detector.py  -- ETF MA200 とマクロニュースで市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント（取得 & 保存）
    - pipeline.py         -- ETL パイプライン (run_daily_etl 等) / ETLResult
    - etl.py              -- ETLResult の再エクスポート
    - stats.py            -- zscore_normalize 等ユーティリティ
    - quality.py          -- データ品質チェック
    - audit.py            -- 監査ログ用 DDL / init_audit_db
    - news_collector.py   -- RSS 収集と前処理
    - calendar_management.py -- market_calendar 管理と営業日判定
  - research/
    - __init__.py
    - factor_research.py  -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/... (上記ファイル)
  - (その他) strategy/, execution/, monitoring/ はパッケージ公開リストに含まれるが、このスニペットでは data / ai / research を中心に実装されています。

---

開発・運用上の注意
- DuckDB の executemany に関するバージョン差異（空リストの扱い等）に注意しており、実装内でその互換性を考慮しています。
- 外部ネットワークアクセス（RSS / J-Quants / OpenAI）は失敗時のフェイルセーフとリトライを実装していますが、API キーやレート制限などの運用管理は利用者側で行ってください。
- 監査ログは削除しない前提で設計されています（トレーサビリティ確保）。
- セキュリティ: RSS 取得で SSRF 対策、XML パースに対する defusedxml 利用、URL 正規化等の保護処理を含みます。

---

ライセンス / 貢献
- 本 README では省略しています。実際のプロジェクトでは LICENSE ファイルを同梱してください。
- 貢献やバグレポートは Pull Request / Issue を通じて行ってください。

---

この README はコードベースの実装から生成した要約です。より詳細な設計意図や API の細かい挙動は各モジュールの docstring を参照してください。