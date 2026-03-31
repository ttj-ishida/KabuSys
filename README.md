KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援ライブラリです。
主に以下を提供します。

- J-Quants API からの差分ETL（株価・財務・マーケットカレンダー）
- ニュースの収集・NLP による銘柄センチメント付与（OpenAI）
- 市場レジーム判定（MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック、監査ログ（発注→約定トレーサビリティ）
- DuckDB を用いたローカルデータストア操作ユーティリティ群

設計上の注目点
- ルックアヘッドバイアス対策：内部処理は基本的に date/target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計（バックテストに安全）。
- 冪等性：DB 保存は基本的に ON CONFLICT DO UPDATE / INSERT … ON CONFLICT を用いる。
- フェイルセーフ：外部API失敗時は可能な範囲でフォールバックする（例: LLM の失敗時に中立スコアを使う等）。
- セキュリティ考慮：RSS収集でのSSRF対策、XMLパースの安全化（defusedxml）など。

主な機能一覧
----------------
- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants との通信（jquants_client）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への保存
- AI/NLP（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントを ai_scores に書き込み
  - score_regime: ETF（1321）MA200乖離とマクロニュースで市場レジーム判定
- 研究用モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等
- 監査ログ（kabusys.data.audit）
  - 監査用テーブル作成・初期化（signal_events, order_requests, executions）
- 設定管理（kabusys.config）
  - .env 自動ロード、環境変数ラッパー（settings）

必要条件（概略）
----------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外のパッケージは requirements.txt にまとめてください）

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 例: git clone <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD      — kabuステーション API のパスワード（運用時）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - OpenAI を使用する機能を使う場合:
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用。関数引数からも渡せます）
   - データベースパス（任意、デフォルトあり）
     - DUCKDB_PATH  （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH  （監視系: data/monitoring.db）

5. サンプル .env（プロジェクトルートに置く）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

基本的な使い方（例）
--------------------

1) DuckDB 接続準備（Python REPL やスクリプト）

```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（ETL が J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日を対象
print(result.to_dict())
```

3) ニュース NLP（OpenAI を用いて銘柄別 ai_scores を生成）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 指定日分（例: 2026-03-20 のニュースウィンドウ）についてスコア算出
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> 環境変数 OPENAI_API_KEY を使用
print(f"written {n} scores")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
print("done", res)
```

5) 監査ログ DB 初期化（監査用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて監査テーブルが作成されていることを確認できます
```

注意点（実装に関する補足）
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を利用する実装になっています。API レスポンスの整形や再試行ロジックが組み込まれていますが、API バージョンや SDK の変更があれば適宜対応が必要です。
- ETL / calendar update などはネットワーク I/O を伴います。ID トークンの自動リフレッシュやレート制限（J-Quants: 120 req/min）に対応する実装があります。
- news_collector は RSS の正規化・SSRF 防御・XML の安全パースを行います。

主要モジュール / ディレクトリ構成
---------------------------------
（src/kabusys 以下の主なファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env ロード / settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py          — J-Quants API クライアント & 保存処理
    - news_collector.py          — RSS 収集と前処理
    - calendar_management.py     — マーケットカレンダー管理（is_trading_day 等）
    - quality.py                 — データ品質チェック
    - stats.py                   — zscore_normalize 等の汎用統計ユーティリティ
    - audit.py                   — 監査ログテーブルの定義・初期化
    - etl.py                     — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py         — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py     — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/、data/、research/ 以下にさらに補助関数や補助モジュールあり

運用上のヒント
----------------
- 本番環境では KABUSYS_ENV を "live" にしてログレベルや送信先などを区別してください。
- ETL のスケジュールは cron や Airflow、任意のジョブランナーで daily 実行する想定です。calendar ETL は先に実行して営業日調整に用います。
- DuckDB ファイルはバックアップを取り、監査 DB は削除しないポリシーで運用するのが妥当です。
- テストやCIで環境変数の自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

ライセンス・貢献
----------------
- 本リポジトリ内にライセンスファイルが存在しない場合はプロジェクト所有者に確認してください。
- 貢献やバグ修正は PR を作成してください。重大な設計変更（API仕様や DB スキーマ変更）は事前に issue で相談してください。

サポート / 問い合わせ
--------------------
- Slack やメールなど、プロジェクトの既定の連絡手段を用いてください。README の最後に連絡先が必要であれば追加してください。

以上。必要であれば README に含めるセットアップコマンドや具体的な Docker / systemd の設定例、より詳細な API 使用例（SQL スキーマや例外ハンドリング含む）を追加します。どの部分を補足しましょうか？