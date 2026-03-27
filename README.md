# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants（株価・財務・カレンダー）、OpenAI（ニュースセンチメント）、kabuステーション（発注）などと連携して、データ収集（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的のために設計された Python パッケージです。

- J-Quants API を用いた株価/財務/カレンダーデータの差分取得（ETL）と DuckDB への保存
- ニュース記事の収集・前処理・LLM による銘柄別センチメント分析（gpt-4o-mini を想定）
- マーケットレジーム（bull/neutral/bear）判定（ETF の MA200 乖離 + マクロニュースセンチメント）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- 研究用途のファクター計算・特徴量解析ユーティリティ

設計上の重要点：
- ルックアヘッドバイアスを避けるように datetime.today()/date.today() を不必要に参照しない実装
- 外部 API 呼び出しはリトライやフェイルセーフを組み込み、部分失敗でも安全に継続できる設計
- DuckDB を中心に SQL + Python で効率的にデータ処理

---

## 主な機能一覧

- データ収集 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：取得、ページネーション、保存（冪等）
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（kabusys.data.quality）
- ニュース NLP（OpenAI）
  - score_news：銘柄ごとのニュースセンチメントを ai_scores テーブルへ書込み（kabusys.ai.news_nlp）
  - 記事ウィンドウ計算・バッチ送信・レスポンス検証・スコアクリッピング実装
- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）MA200 乖離（70%）とマクロニュース LLM（30%）を合成して日次判定
- 研究ユーティリティ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、SSRF 対策、前処理、raw_news 保存の想定ワークフロー
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db：シグナル・発注・約定の監査用テーブルを初期化

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
   - 例: git clone <repo-url>

2. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限の例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 開発インストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings クラスで参照されるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu API（kabuステーション）用パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャネル ID
   - ほかに利用される変数:
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 呼び出しで参照）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG / INFO / …
     - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
     - SQLITE_PATH           : 監視等で使用する SQLite パス（data/monitoring.db 等）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx...
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

6. データベースディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下はライブラリを直接インポートして使う簡単な使用例です。実行はプロジェクトルートで行ってください。

- DuckDB 接続を作成して ETL を実行する（run_daily_etl）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのセンチメントスコアを取得して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジームをスコアリング（score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使用
```

- 監査ログ用の DuckDB を初期化する:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn を使って監査テーブルにアクセスできます
```

- ニュース RSS を取得（ニュースコレクタの低レベル関数）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"])
```

注意点:
- score_news / score_regime は OpenAI の API を使用します。APIキーが必要です（api_key 引数で明示的に渡すか、OPENAI_API_KEY 環境変数を設定）。
- J-Quants API 呼び出しには有効な JQUANTS_REFRESH_TOKEN が必要です。
- DuckDB テーブルスキーマや初期化の手順はプロジェクトの別ファイル（schema 初期化機能など）に依存するため、ETL 実行前にスキーマが準備されていることを確認してください（init_audit_schema は監査用スキーマのみを作成します）。

---

## 開発者向けメモ

- 環境変数の自動読み込みは、パッケージ import 時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して .env / .env.local を読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI への呼び出しはモジュール内部で _call_openai_api として分離しており、テストではモックしやすい設計になっています（unittest.mock.patch を利用）。
- J-Quants API クライアントは固定間隔レート制御（120 req/min）とリトライ・トークン自動リフレッシュを実装しています。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン差があるため、コード内で空チェックを行っています。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なモジュールと役割（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py           - ニュースの LLM センチメント分析（score_news）
    - regime_detector.py    - マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     - J-Quants API クライアント（fetch / save 関数）
    - pipeline.py           - ETL パイプライン（run_daily_etl 等）
    - quality.py            - データ品質チェック
    - news_collector.py     - RSS ニュース収集ユーティリティ
    - calendar_management.py- 市場カレンダー管理 / 営業日判定
    - audit.py              - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - stats.py              - 共通統計ユーティリティ（zscore_normalize）
    - etl.py                - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    - ファクター計算（momentum/value/volatility）
    - feature_exploration.py- 将来リターン / IC / 統計サマリー等

（加えて strategy/, execution/, monitoring/ といったパッケージ名は __all__ に定義されていますが、実装はこのリポジトリの範囲に依存します。）

---

## トラブルシューティング / 注意事項

- OpenAI API のレスポンス検証失敗や API の一時的障害時は多くの箇所でフェイルセーフ（スコア 0.0 を採用、処理継続）を行います。運用時はログを適切に監視してください。
- J-Quants の API レート制限・ページネーションに対応していますが、ID トークンの期限切れ等に備えてログと再実行戦略を用意してください。
- DuckDB のバージョン差異に起因する挙動（executemany の空リストなど）に注意してください。
- 本ライブラリは実トレード／本番運用のために設計されていますが、発注ロジック・リスク管理・資金管理は各自の運用ポリシーに基づいて実装・確認してください。

---

必要であれば、README にサンプル .env.example、より詳しい DB スキーマ、テスト実行方法、CI 設定などのセクションを追加します。追加希望があれば教えてください。