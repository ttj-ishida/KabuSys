# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含みます。

---

## 概要

KabuSys は日本株の自動売買・研究基盤向けに設計された Python モジュール群です。主な設計方針は以下です。

- Look-ahead bias を排除するため、内部処理はすべて明示的な target_date に基づく（date.today() を勝手に参照しない）。
- DuckDB をデータストアとして使用し、ETL は冪等（ON CONFLICT / UPDATE）で実行。
- J-Quants API とのやり取りはレートリミット・リトライ・トークン自動リフレッシュを実装。
- ニュースの収集・NLP（OpenAI）呼び出しは堅牢なエラーハンドリングとバッチ処理を備える。
- 監査ログ（signal/order/execution）によりシグナルから約定までを完全トレース可能。

バージョン: 0.1.0

---

## 主な機能一覧

- data
  - ETL: J-Quants からの prices / financials / market calendar の差分取得・保存（kabusys.data.pipeline）
  - カレンダー管理（営業日判定 / next/prev_trading_day 等）
  - News collector: RSS 収集・正規化（SSRF 対策、トラッキングパラメータ削除）
  - J-Quants クライアント（認証、自動リフレッシュ、ページネーション、保存関数）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）初期化・DB 作成
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュースセンチメント（score_news）：銘柄ごとの ai_score を生成して ai_scores テーブルへ保存
  - 市場レジーム判定（score_regime）：ETF(1321)のMA乖離とマクロセンチメントを合成して market_regime を作成
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - 環境変数読み込み（.env / .env.local 自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で設定値取得

---

## セットアップ手順

前提:
- Python 3.10+（typing の union 演算子などを使用）
- 必要な外部サービスの API キー（J-Quants, OpenAI など）

1. リポジトリを取得
   - git clone / ダウンロード

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （なければ次の主要依存をインストール）
   - pip install duckdb openai defusedxml

   （必要に応じて logging 等のライブラリを導入してください）

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数（.env）を作成  
   プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（tests 等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   OPENAI_API_KEY=あなたの_openai_api_key
   KABU_API_PASSWORD=あなたの_kabu_api_password
   SLACK_BOT_TOKEN=あなたの_slack_bot_token
   SLACK_CHANNEL_ID=チャンネルID
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（基本例）

以下はライブラリの代表的な使い方例です。いずれも DuckDB 接続を渡して実行します。

1. DuckDB 接続を作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL を実行（株価・財務・カレンダー取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定すればその日を基準に実行
print(result.to_dict())
```

3. ニュースセンチメントを生成して ai_scores へ書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

4. 市場レジームスコアを計算して market_regime へ書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5. 監査ログ用 DuckDB を初期化（監査用DBファイルを新規作成してスキーマを投入）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

6. ファクター計算・研究用関数
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

7. 設定参照（settings）
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

補足:
- OpenAI API キーは score_news / score_regime の api_key 引数で上書き可能。引数が None の場合は環境変数 OPENAI_API_KEY を使用します。
- config モジュールは .env/.env.local 自動ロード機能を持っています。テストで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使う CLI/スクリプトの例

（プロジェクトには CLI は付属していない想定。簡単な cron / バッチの例）

- 日次夜間バッチ（ETL + ニュース + レジームスコア）
```bash
python - <<'PY'
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn)
score_news(conn, target_date=res.target_date)
score_regime(conn, target_date=res.target_date)
PY
```

---

## 設計上の注意点 / 振る舞い

- Look-ahead bias 対策: 多くの関数は target_date を引数として受け取り、内部で未来データを参照しないように設計。
- 冪等性: ETL や保存関数は ON CONFLICT を使い上書き・重複防止を行うため何度実行しても安全な設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）の失敗は適切にログ出力・リトライし、致命的でない場合は処理を継続する（例: LLM 失敗時はゼロスコアでフォールバック）。
- セキュリティ: news_collector は SSRF 対策・圧縮応答サイズ制限・XML parsing の安全化（defusedxml）を実施。

---

## 主要ディレクトリ構成

概要（src/kabusys 以下の主なファイル）:

- kabusys/__init__.py
- kabusys/config.py
  - 環境変数の自動読み込み・settings オブジェクト
- kabusys/data/
  - __init__.py
  - jquants_client.py         : J-Quants API クライアント（fetch/save 関数）
  - pipeline.py               : ETL パイプラインと run_daily_etl 等
  - calendar_management.py    : 市場カレンダー管理（is_trading_day 等）
  - news_collector.py         : RSS 収集・前処理・保存ロジック
  - quality.py                : データ品質チェック（missing / spike / duplicates / date_consistency）
  - stats.py                  : zscore_normalize 等統計ユーティリティ
  - audit.py                  : 監査ログテーブル定義・初期化（signal/order/execution）
  - etl.py                    : ETLResult の再エクスポート
- kabusys/ai/
  - __init__.py
  - news_nlp.py               : ニュースの LLM スコアリング（score_news）
  - regime_detector.py        : マクロ sentiment + MA 乖離で市場レジーム判定（score_regime）
- kabusys/research/
  - __init__.py
  - factor_research.py        : momentum/value/volatility 計算
  - feature_exploration.py    : forward returns, IC, factor_summary, rank
- その他
  - settings による DU CKDB/SQLite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）

---

## 依存関係（主なもの）

- Python >= 3.10
- duckdb
- openai
- defusedxml

※ プロジェクトルートに requirements.txt を用意することを推奨します。

---

## ライセンス・貢献

この README はリポジトリ内コード（示されたモジュール群）を基に作成されています。  
実運用・配布時はライセンス表記、貢献ガイドライン、テストの追加、CI 設定等を別途整備してください。

---

README に記載してほしい追加情報（例: 実行スクリプト、CI、DB スキーマ定義、.env.example）や、特定の使い方のサンプルがあれば教えてください。README をその内容に合わせて更新します。