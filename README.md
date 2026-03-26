# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（部分実装）。  
DuckDB をバックエンドにデータ ETL、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、調査用ファクター計算、マーケットカレンダー管理、監査ログ初期化等のユーティリティを提供します。

注意: このリポジトリはフルプロダクトの一部実装を含みます。実運用前に十分なテストと安全対策（発注ロジックの保護、実環境での API 制限管理等）を行ってください。

---

## 主な特徴

- ETL / Data Platform
  - J-Quants API との差分取得（株価日足 / 財務 / 市場カレンダー）と DuckDB への冪等保存
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース & AI
  - RSS 収集（安全対策付き）と raw_news 保存ユーティリティ
  - OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメント算出（ai_scores テーブル）
  - マクロニュースと ETF 200日移動平均乖離を合成した市場レジーム判定（bull/neutral/bear）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、ファクター統計サマリ
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル定義と初期化ユーティリティ
- 設定管理
  - .env ファイルと環境変数の読み込み（プロジェクトルート検出、自動ロード）

---

## 必要な環境変数

主に以下を利用します（最低限必要なもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用）
- KABUSYS_ENV — 環境: `development` | `paper_trading` | `live`（省略時 `development`）
- LOG_LEVEL — ログレベル: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（省略時 `INFO`）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

設定用ユーティリティ:
```py
from kabusys.config import settings
# 例:
token = settings.jquants_refresh_token
db_path = settings.duckdb_path  # Path オブジェクト
```

---

## セットアップ手順（開発用）

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（代表的なもの）
   - pip install duckdb openai defusedxml
   - （必要に応じて追加: requests 等）
4. パッケージとしてインストール（開発モード推奨）
   - pip install -e .
   - （pyproject.toml/setup.py がある場合）
5. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境に設定
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
6. データディレクトリ作成（config のデフォルト）
   - data/ 配下に DuckDB ファイル等が作成されます（settings.duckdb_path デフォルト: data/kabusys.duckdb）

---

## 使い方（主要な API）

※ DuckDB は接続オブジェクト（duckdb.connect(...)）を各関数に渡します。

- 日次 ETL 実行
```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアリング（1日分）
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```
OPENAI_API_KEY は環境変数にセットするか、score_news の引数 api_key に渡せます。

- 市場レジーム判定（ETF 1321 ベース + マクロニュース）
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb 接続を返します
```

- 研究用ファクター（例: モメンタム）
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{'date': ..., 'code': 'XXXX', 'mom_1m': ..., ...}, ...]
```

---

## 主要モジュールと機能一覧

（コードベースに含まれる主要なモジュールとその役割）

- kabusys.config
  - 環境変数/.env 読み込み、Settings クラス（設定値取得）
- kabusys.ai
  - news_nlp.score_news: ニュース (raw_news) → ai_scores（OpenAI を使用）
  - regime_detector.score_regime: マクロ + ETF MA200 で市場レジーム判定
- kabusys.data
  - pipeline.py: ETL の中核（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - jquants_client.py: J-Quants API クライアント、fetch/save 関数（rate limit・retry・token 管理）
  - news_collector.py: RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - calendar_management.py: market_calendar 管理（is_trading_day 等）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py: z-score 正規化など統計ユーティリティ
  - audit.py: 監査ログスキーマ初期化・init_audit_db
  - etl.py: ETLResult の再エクスポート
- kabusys.research
  - factor_research.py: モメンタム/ボラティリティ/バリュー系ファクター
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数

付帯:
- src/kabusys/__init__.py: パッケージメタ情報（__version__ 等）

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下を想定）

- src/
  - kabusys/
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
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/ (他の研究ユーティリティ)
    - (strategy/, execution/, monitoring/ は __all__ に含まれるが本スナップショットでは実装が限定的)

---

## 注意事項 / 運用上の留意点

- OpenAI / J-Quants / その他外部 API の呼び出しにはレート制限とコストが伴います。キーの管理・呼び出し頻度の制御を行ってください。
- ニュース収集・RSS パースにおいては SSRF や XML 攻撃対策を実装していますが、運用に合わせた追加のセキュリティ検査を推奨します。
- DuckDB の executemany や型制約に起因する挙動（空リストの挿入不可等）を考慮済みですが、DuckDB バージョン差異に注意してください。
- 実際の発注ロジック（kabu ステーション等）と接続する際は、二重発注防止のため監査ログの order_request_id を使った冪等制御が必須です。
- 本 README はコードベースのスナップショットに基づく要約です。詳細は各モジュールの docstring を参照してください。

---

## 開発 / 貢献

- バグ報告や機能改善は Issue を作成してください。
- 新しい機能を追加する場合はユニットテストと基本的なドキュメントを追加してください。

---

必要であれば、README に含めるサンプル .env.example、より詳細なセットアップ（CI、テスト、ロギング設定）、あるいは API 使用例（J-Quants の取得例・OpenAI レスポンスの期待フォーマット）を追加で作成します。どの情報を拡張しますか？