# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動化されたデータパイプラインと研究・取引支援ロジックを提供する Python パッケージです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース収集・NLP による銘柄別センチメントスコア生成（OpenAI を利用）
- マクロ + テクニカルを組み合わせた市場レジーム判定（ETF 1321 の MA200 等）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution の追跡）用スキーマ初期化、監査 DB ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計上の特徴:
- DuckDB をデータレイクに利用し SQL と Python を併用
- OpenAI（gpt-4o-mini）を JSON mode で呼ぶためレスポンスパース/リトライ等に配慮
- Look-ahead bias 回避のため日付参照の扱いに注意（内部で date.today() を直接使わない設計）
- 冪等操作（ON CONFLICT / INSERT … DO UPDATE）を重視

---

## 機能一覧

- データ（kabusys.data）
  - ETL: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（fetch/ save 関数）
  - マーケットカレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS）と前処理（news_collector）
  - データ品質チェック（quality）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- 研究（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン計算、IC 計算、factor_summary など
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出 → ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロセンチメントを合成して market_regime に書き込み
- 設定（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート基準）
  - 環境変数から Settings オブジェクト（settings）を提供

---

## セットアップ手順

以下は開発環境での一般的な手順です。

1. Python 環境の準備（推奨: 3.10+）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存例（手動インストール）:
     - pip install duckdb openai defusedxml

   ※ 実際のパッケージ一覧はプロジェクトの pyproject.toml / requirements に従ってください。

3. パッケージのインストール（開発モード）
   - プロジェクトルートにて:
     - pip install -e .

4. 環境変数 (.env)
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は .env を上書き）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
   - SLACK_BOT_TOKEN       : Slack 通知が必要な場合の Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注など）
   - OPENAI_API_KEY        : OpenAI を使う関数（score_news, score_regime）で必要
   - オプション:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
```

---

## 使い方（主要な API/実行例）

以下は Python REPL やスクリプトからの簡易的な利用例です。DuckDB 接続には duckdb.connect(path) を使用します。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
print(f"written {count} codes")
```

- 市場レジームをスコアリングして market_regime に保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
```

- 監査ログ用の DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄のモメンタム情報リスト
```

注意:
- AI 関連関数は OpenAI の API を利用します。API キーと課金設定に注意してください。
- run_daily_etl 等は内部で J-Quants API を呼ぶため JQUANTS_REFRESH_TOKEN が必要です。

---

## ディレクトリ構成（主なファイル）

以下は主要モジュールを抜粋した構成（src/kabusys 以下）です。実際の追加ファイルやテストはプロジェクトに依存します。

- src/kabusys/
  - __init__.py
  - config.py        — 環境変数 / Settings の管理 (.env 自動ロード)
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（score_news）
    - regime_detector.py  — レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save/認証・レート制御）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py  — RSS 収集・正規化
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - monitoring/ (README にあれば監視用コードがここに入る想定)
  - execution/ (発注・約定のラッパー等を置く想定)
  - strategy/ (戦略ロジックを置く想定)

---

## 運用上の注意

- 環境変数はプロジェクトルートの .env / .env.local から自動読み込みされます。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出しはレート制限や失敗を考慮したリトライ処理を実装していますが、API コストや制限に注意してください。失敗時はフェイルセーフ（多くの場合 0.0 スコアなどで継続）設計です。
- ETL は差分取得とバックフィルをサポートしていますが、初回ロードや大規模バックフィル時は API レート制限・実行時間を考慮して段階的に実行してください。
- DuckDB の executemany で空リスト渡すとエラーになるバージョンがあるため、空チェックが行われています。
- 監査ログテーブルは削除しない前提です。スキーマ初期化は冪等で実施しますが本番 DB に適用する際はバックアップを推奨します。

---

## 開発・貢献

バグ報告や機能提案は Issue を投げてください。プルリクエストは一貫したスタイルとテストを付けて送ってください。

---

以上が簡易 README.md です。必要であれば利用例（CLI スクリプト、cron/airflow でのスケジューリング例）や .env.example のテンプレート、依存関係の正確な一覧（requirements.txt / pyproject.toml）を追記します。どの情報を追加しますか？