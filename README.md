# KabuSys

日本株向けのデータプラットフォーム / 研究・自動売買基盤のコアライブラリです。  
ETL、データ品質チェック、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含みます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要なエントリポイント例）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は J-Quants（日本株データ）や RSS ニュース、OpenAI（LLM）を組み合わせて
  データ収集（ETL）→ 品質チェック → ニュースベースのセンチメント評価 → 研究/シグナル生成 → 発注監査を支援する Python ライブラリ群です。
- Look-ahead bias を避ける設計思想（target_date を明示、将来データを参照しない等）や、API のリトライ／レート制限管理、DuckDB ベースの永続化、冪等保存を重視しています。

---

主な機能
- ETL パイプライン（kabusys.data.pipeline）
  - 株価日足、財務データ、JPX カレンダーの差分取得と DuckDB への保存
  - 品質チェック（欠損、スパイク、重複、日付整合性）
  - ETL 実行結果は ETLResult で返却
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ページネーション・レート制御・自動トークンリフレッシュ付き
  - fetch / save 関数（daily quotes / financial statements / market calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、SSRF/サイズ制限、正規化、raw_news への冪等保存設計
- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini / JSON モード）で記事群を銘柄ごとにスコア化し ai_scores に保存
  - チャンク送信、リトライ、レスポンス検証、±1 にクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily の regime を判定・保存
- 研究ユーティリティ（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Z-score 正規化
- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar を利用した営業日判定・前後営業日取得など
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 監査 DB の初期化（init_audit_db / init_audit_schema）
- 汎用統計ユーティリティ（kabusys.data.stats）

---

セットアップ手順（開発／実行環境の例）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境を用意（推奨: 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 最小で必要なライブラリ例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があればそれを利用してください）
4. 環境変数（.env）を作成
   - 下記「環境変数（.env）例」を参照
   - パッケージの自動 .env ロードはデフォルトで有効（プロジェクトルートに .env/.env.local を配置）  
     → 自動ロードを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データベースディレクトリの準備
   - settings.duckdb_path のデフォルトは data/kabusys.duckdb（フォルダが無ければ自動作成されますが、環境に合わせてパスを調整してください）

注意:
- OpenAI API を使う処理（news_nlp / regime_detector）は環境変数 OPENAI_API_KEY か関数引数で API キーを渡す必要があります。
- J-Quants の API 利用にはリフレッシュトークンが必要です（JQUANTS_REFRESH_TOKEN）。

---

環境変数（.env）例
以下は本ライブラリで参照される主な環境変数の例です（必要なもののみ設定してください）。

例 .env:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# OpenAI（news_nlp / regime_detector）
OPENAI_API_KEY=sk-...

# DB パス等
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 監視設定・その他
PID_FILE_PATH=data/execution.pid
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0

# アプリ環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を起点）に .env（優先度低） と .env.local（優先度高）を読み込みます。
- テストや特別なケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます。

---

使い方（主要な API / 実行例）

準備: DuckDB 接続の取得（例）
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 対象日を明示して実行（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュース NLP スコアリングを実行する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続、OPENAI_API_KEY を環境に設定しておくか api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（監査テーブルを別 DB に分けたい場合など）
```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB、またはパスを指定
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルが作成済みの DuckDB 接続
```

5) 研究用ユーティリティ例（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

注意点:
- LLM 呼び出し（OpenAI）にはリトライやフェイルセーフが組み込まれていますが、APIキー・レート制限（OpenAI 側）や利用コストに注意してください。
- J-Quants API はレート制限を遵守するため内部でスロットリング処理を行います。認証トークンの自動リフレッシュも実装済みです。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                     — 設定 / 環境変数ロード
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL インターフェース（ETLResult 再エクスポート）
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - news_collector.py            — RSS 収集（raw_news）
    - calendar_management.py       — 市場カレンダー管理・営業日ロジック
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査テーブル作成 / 初期化
    - stats.py                     — z-score 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
  - monitoring/ (コードベースに存在する想定の監視モジュール／ファイル群)
  - execution/  (発注・約定の実行モジュール等 想定)
  - strategy/   (戦略実装関連)

（注）コードベースにはさらに細かい関数・ユーティリティが多数あります。上記は主要なモジュールの概観です。

---

運用上の注意
- 機密情報（API キー・トークン）は .env や環境変数で管理し、ソース管理に含めないでください。
- DuckDB ファイルや監査 DB のバックアップ、権限管理を適切に行ってください。
- J-Quants / OpenAI のレート制限・コストに注意してください（本ライブラリはリトライやスロットリングを備えていますが、健全な運用ポリシーが必要です）。
- LLM の出力に依存するロジックは不確実性があるため、プロダクションでの自動売買に適用する前に十分な検証を行ってください。

---

この README はコードベースの現状実装（主要モジュール）に基づいて作成しています。さらに具体的な使い方（CI/CD、Docker 化、運用スクリプト、テスト実行方法など）が必要であれば、プロジェクトの意図に合わせて追記できます。