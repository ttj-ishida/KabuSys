# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、監査ログなど、取引・リサーチ・データ基盤に必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（主要）
- ディレクトリ構成

---

プロジェクト概要
- 日本株（JPX）データの取得・整備（J-Quants API 経由）と品質チェック。
- ニュース記事の収集と LLM によるセンチメント付与（gpt-4o-mini を想定）。
- ニュースの銘柄紐付け → 銘柄別 AI スコアの保存。
- ETF を用いた市場レジーム判定（MA200 とマクロニュースの混合スコア）。
- リサーチ用：モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン・IC 計算、Z スコア正規化。
- 取引監査ログ（signal / order_request / executions）用スキーマの初期化ユーティリティ。
- カレンダー管理（JPX 営業日判定、next/prev/trading days）。
- DuckDB を主要なローカル DB として利用（データ格納・処理）。

---

機能一覧（主なモジュール）
- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数経由で各種設定を取得
- kabusys.data.jquants_client
  - J-Quants からの株価・財務・カレンダー取得（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL：run_prices_etl、run_financials_etl、run_calendar_etl
  - ETLResult クラスによる結果集約
- kabusys.data.quality
  - 欠損、スパイク、重複、日付整合性チェック
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（J-Quants から差分取得して DB 更新）
- kabusys.data.news_collector
  - RSS 取得・前処理・SSRF/サイズ/スキーム対策・raw_news への保存ロジック
- kabusys.data.audit
  - 監査ログスキーマ（signal_events / order_requests / executions）作成
  - init_audit_schema / init_audit_db
- kabusys.ai.news_nlp
  - ニュースを銘柄ごとに集約し LLM でセンチメント（JSON mode 想定）を取得 → ai_scores 保存
  - calc_news_window（ニュース対象ウィンドウ計算）
- kabusys.ai.regime_detector
  - ETF(1321) の MA200 乖離 + マクロニュースセンチメントを合成して market_regime に書き込み
- kabusys.research
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

セットアップ手順（ローカル開発用）
前提
- Python 3.10 以上（| 型ヒントやモダンな型注釈を使用）
- Git（.git をプロジェクトルート検出で使用）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール
   - 必須（本コードで参照される代表パッケージ）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 実運用では他に slack_sdk 等も必要になる可能性があります（通知などを行う場合）。

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成して必要変数を設定できます。
   - 自動ロードは kabusys.config によりプロジェクトルートの .env / .env.local から行われます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

主要な環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI calls) — OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack Bot Token（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（通知用）
- DUCKDB_PATH — デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視関連
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

設定が不足している必須項目を参照すると Settings 側で ValueError が発生します。

---

簡単な使い方（コード例）

以下は最小限の使い方例です。実際はログ設定・例外処理・API キー管理等を適切に行ってください。

1) DuckDB 接続と日次 ETL の実行
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコア付与（LLM）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} ai scores")
```

3) 市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査 DB 初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査ログ用のテーブルとインデックスが作成されます
```

5) 研究用ユーティリティ
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

6) カレンダー判定
```
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
is_trade = is_trading_day(conn, date(2026,3,20))
next_day = next_trading_day(conn, date(2026,3,20))
```

注意点
- LLM 呼び出し（score_news / score_regime）は OpenAI の API キーが必要です。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- 各関数はルックアヘッドバイアスを避ける設計（内部で date.today() 等を直接参照しないように）になっています。バックテスト用途にも配慮されていますが、バイアス管理は利用者側でも注意してください。
- news_collector は RSS の取得時に SSRF / サイズチェック / XML セキュリティ対策を施しています。

---

ディレクトリ構成（主なファイル）
（src/kabusys をルートとした主要ファイルを抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/... その他ユーティリティ

---

開発・運用上の注意
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読みます。テスト時や外部環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化できます。
- J-Quants API のレート制限（120 req/min）への対処やリトライ/トークンリフレッシュは jquants_client に組み込まれていますが、並列処理時は別途注意が必要です。
- DuckDB の executemany に関する制約や、部分書き換えによる冪等性（ai_scores など）を考慮した設計になっています。

---

ライセンス・貢献
- （ここにライセンス情報と貢献ルールを追記してください）

---

以上。README の追加や、利用例の拡張、CI / テスト例の追加が必要であれば教えてください。