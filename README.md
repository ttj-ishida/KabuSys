# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ。  
J-Quants / JPX からのデータ取得（ETL）、ニュース収集とAIによるニュースセンチメント評価、ファクター計算、監査ログスキーマなどを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない）
- DuckDB をデータストアとして使用し、SQL + Python の組合せで処理
- API 呼び出しに対する堅牢なリトライ / レート制御
- ETL・品質チェックは部分失敗を許容しつつ問題を集約して報告
- 監査ログは冪等かつトレーサビリティを維持

---

## 機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git / pyproject.toml を探索）
  - 必須環境変数チェック（Settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル、品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 実行結果を ETLResult で集約
- ニュース収集
  - RSS フィード取得（SSRF / 大容量対策 / トラッキングパラメータ除去）
  - raw_news テーブルへの冪等保存、news_symbols との紐付け
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げ、センチメントを ai_scores に保存（score_news）
  - マクロ記事を用いた市場レジーム判定（ETF 1321 MA200 乖離 + LLM マクロセンチメント）→ market_regime（score_regime）
  - JSON Mode を利用した厳密なレスポンス期待、エラー時のフォールバック
- 研究用ユーティリティ
  - ファクター作成（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化関数
  - init_audit_db で監査用 DuckDB を初期化

---

## 必要条件（推奨）
- Python 3.10 以上（型注釈に | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス：J-Quants API / OpenAI API / RSS フィード など

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください）

---

## セットアップ手順（ローカル開発向け）
1. Python 環境を準備（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements ファイルがあればそれを使用してください。

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須（/ 想定される）環境変数例:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token 用）
   - KABU_API_PASSWORD: kabu API パスワード（設定項目として存在）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知用チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で参照）
   - DUCKDB_PATH / SQLITE_PATH: （任意）データベースパス（デフォルトは data/kabusys.duckdb / data/monitoring.db）

4. DuckDB 初期スキーマの準備
   - 本リポジトリにはスキーマ初期化のためのユーティリティが含まれています（例: audit.init_audit_db）。
   - 適宜 SQL スクリプトや schema モジュールを用いて必要テーブルを作成してください。

---

## 使い方（簡易例）
以下はライブラリの一部 API を直接呼び出す例（対話型 / スクリプトから）。

- DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
# OPENAI_API_KEY が環境にある場合は api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を保持して監査テーブルを利用
```

- 設定値にアクセスする
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 環境変数と自動 .env ロード挙動
- モジュール kabusys.config は起動時にプロジェクトルート（.git または pyproject.toml を探索）を特定し、`.env` → `.env.local` の順で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Settings クラスで必須変数が参照されると未設定時に ValueError を投げます（明示的な失敗で早期検出）。

---

## 主な公開 API（抜粋）
- kabusys.config.settings — 環境設定アクセサ（jquants_refresh_token, kabu_api_base_url, slack_* 等）
- kabusys.data.jquants_client — get_id_token, fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar など
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のエントリポイント
- kabusys.data.quality.run_all_checks — 品質チェック
- kabusys.ai.news_nlp.score_news — ニュースセンチメント取得 + ai_scores 書込み
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定 + market_regime 書込み
- kabusys.research.* — ファクター計算 / IC / 統計ユーティリティ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

## ディレクトリ構成（抜粋）
プロジェクトの主要モジュール構成を示します（src/kabusys 以下）。

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema / clients / utilities)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*.py（ファクター計算・特徴量探索）
  - (strategy/ execution/ monitoring 等のパッケージも想定されるが本リポジトリでは一部のみ実装)

---

## ログ・監視
- 各モジュールは標準 logging モジュールを利用して情報・警告・エラーを出力します。LOG_LEVEL 環境変数で調整できます（Settings.log_level）。
- ETL/品質チェックは問題を収集して ETLResult に格納します。致命的な問題は errors に追加されます。

---

## 開発・貢献
- 型注釈・ドキュメント文字列を重視しており、ユニットテストによる差し替え（mock）を想定した設計になっています。
- 外部 API 呼び出し部分（OpenAI の呼び出し、HTTP IO 等）はテストでモック化できるよう内部関数を分離しています。

---

## 注意事項
- 本ライブラリは実際の発注処理や実口座操作を含む設計に拡張可能ですが、現行コードベースでは主にデータ・研究・監査基盤を中心に実装されています。実際に発注する前には十分なレビューとテストを行ってください。
- OpenAI / J-Quants 等の API キーは適切に管理し、ログ等に直接出力しないでください。
- DuckDB のバージョンや SQL の互換性に依存する箇所があります（COMMENT に DuckDB バージョン注意あり）。

---

必要であれば、README に「実行例の詳細」「テーブルスキーマ」「unittest 用のモック例」「CI/CD 設定例」などを追加します。どの部分をより詳しく載せたいか教えてください。