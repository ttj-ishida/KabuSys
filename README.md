# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤ライブラリです。  
データのETL、ニュースの収集・NLPスコアリング、ファクター計算、マーケットレジーム判定、監査ログ（トレーサビリティ）など、バックテスト／運用に必要な機能群を提供します。

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPXマーケットカレンダー取得（ページネーション／再試行／レートリミット対応）
  - 差分更新／バックフィル対応の日次 ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
  - データ保存時の冪等処理（DuckDB への ON CONFLICT / UPDATE）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、サイズ上限、トラッキングパラメータ除去）と raw_news への冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（ai_scores へ書き込み）
  - バッチ処理、レスポンスバリデーション、リトライ（429/ネットワーク/5xx）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロ記事の LLM センチメントを重み合成して日次レジーム（bull / neutral / bear）を算出
- 研究用ユーティリティ（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution の階層で冪等かつトレーサブルな監査テーブルを DuckDB に初期化する機能
- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須環境変数の取得ユーティリティ

---

## 動作要件（Prerequisites）

- Python 3.10+
- DuckDB（Python パッケージ）
- OpenAI Python SDK（openai）※ news_nlp / regime_detector で使用
- defusedxml（RSS パースの安全化）
- 標準ライブラリの urllib 等

推奨インストール例:
pip install duckdb openai defusedxml

（実運用では requirements.txt / poetry / pipx 等で仮想環境管理してください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone ...（省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject があればそちらを使ってください）

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（例）:

.env.example:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=your_openai_api_key
    KABU_API_PASSWORD=your_kabu_api_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

- 注意:
  - settings ジェネレータは一部の環境変数を必須とします（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。足りないと ValueError が発生します。
  - OPENAI_API_KEY は AI モジュールの関数で参照されます。引数で明示的に API キーを渡すことも可能です。

---

## 使い方（簡単な例）

以下は Python インタプリタ／スクリプトからの利用例です。適宜 duckdb 接続パスや target_date を設定してください。

1) DuckDB 接続の例
```python
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

2) 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースの NLP スコアを生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

4) 市場レジームスコアを算出して DB に保存する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログデータベースの初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
```

6) J-Quants の ID トークンを明示取得（必要であれば）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## よくある実行フロー（推奨順）

1. 環境変数を設定（.env）
2. DuckDB のコネクション準備（settings.duckdb_path）
3. run_daily_etl でデータを収集・保存
4. (任意) score_news で AI スコアを作成
5. (任意) score_regime でマーケットレジーム判定
6. 監査用 DB の初期化は運用開始時に一度実行

---

## トラブルシューティング

- ValueError: 環境変数が無い
  - 設定されているはずの環境変数が未設定です。README の .env.example を参考に .env を用意してください。
- OpenAI API エラー / レート制限
  - モジュールはリトライとバックオフを実装していますが、API キーや課金枠、レート制限に注意してください。バッチサイズや呼び出し間隔の調整を検討してください。
- DuckDB 関連のエラー
  - DuckDB のバージョン差異により executemany の扱いや型挙動に差が出る場合があります。推奨は最新の安定版 Python 用 DuckDB を使用してください。

---

## ディレクトリ構成（概要）

リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py  — 市場レジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログテーブル初期化・ユーティリティ
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 設計上のポイント（注意事項）

- ルックアヘッドバイアス防止
  - AIモジュール・ETL等は内部で datetime.today()/date.today() を直接参照しない実装方針（関数に target_date を渡す形）です。バックテスト用途に配慮しています。
- 冪等性
  - ETL・保存処理は可能な限り冪等（ON CONFLICT DO UPDATE / INSERT RETURNING 等）に設計されています。
- フェイルセーフ
  - 外部API（OpenAI/J-Quants）失敗時はフェイルセーフの挙動（スコア0.0やスキップ）になるようにし、処理全体が止まらない設計です（ただしエラーはログ出力／ETLResult へ記録されます）。
- セキュリティ対策
  - RSS 取得は SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限などを行っています。

---

## 貢献・拡張

- 機能追加・バグ修正は PR を歓迎します。AI モジュールのモデル切替、ニュースソース追加、監査スキーマの拡張などが考えられます。
- テスト追加（ユニット/統合）は重要です。外部API呼び出し部分はモック化してテストを行ってください（コード内でもモックを想定した差し替えポイントを用意しています）。

---

README の補足や具体的なサンプル（CI 設定、requirements、Dockerfile 等）が必要であれば、使用想定ケースに合わせて追加で作成します。必要な内容を教えてください。