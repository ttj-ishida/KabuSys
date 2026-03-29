# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・データ品質チェック・ニュース収集・AI（LLM）によるニュースセンチメント評価・市場レジーム判定・監査ログなど、取引システムやリサーチ環境で必要となる機能群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 前提条件
- インストールとセットアップ
- 環境変数 (.env)（例）
- 使い方（簡易コード例）
- ディレクトリ構成（主要ファイル一覧）

---

## プロジェクト概要
KabuSys は日本株を対象にしたデータ収集（J-Quants API）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、戦略用ファクター計算、監査ログ（約定トレーサビリティ）などをまとめたライブラリです。  
バックテストや自動売買システム、研究（research）環境で利用できるよう設計されており、Look-ahead バイアス対策や冪等性、リトライやレート制御など実運用を意識した実装がなされています。

---

## 主な機能
- Data ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得 / 保存（DuckDB）
  - run_daily_etl を中心とした日次 ETL パイプライン
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS フィード収集（SSRF対策、URL正規化、前処理）と raw_news への保存
- AI / NLP
  - ニュースをまとめて OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出（score_news）
  - マクロニュース + ETF(1321)の MA200 乖離から市場レジームを判定（score_regime）
- リサーチ支援
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions などを管理する監査テーブルの初期化・DB準備

---

## 前提条件
- Python 3.10+ 推奨
- 利用ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants、OpenAI 等）
- J-Quants のリフレッシュトークン、OpenAI APIキー、kabu API パスワード、Slack トークンなど各種外部サービスの認証情報

---

## インストールとセットアップ

1. リポジトリをクローン / パッケージを配置
2. 仮想環境を作成し有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要なパッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements / pyproject があればそちらに従ってください。

4. 環境変数を設定（.env をプロジェクトルートに配置すると自動読み込みされます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   例は下記参照。

---

## 環境変数 (.env) 例
以下の環境変数が利用されます（必須項目は明記）。

必須:
- JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
- OPENAI_API_KEY=（OpenAI API キー）
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- SLACK_BOT_TOKEN=（Slack Bot Token）
- SLACK_CHANNEL_ID=（Slack チャネル ID）

任意 / デフォルトあり:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development / paper_trading / live
- LOG_LEVEL=INFO

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（基本的なコード例）

以下は代表的な使い方例です。実行前に上記環境変数を設定してください。

- DuckDB 接続を作る（監査 DB 初期化例）
```python
from kabusys.data.audit import init_audit_db
# ファイル DB を作成して監査スキーマを初期化
conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で OPENAI_API_KEY を使用
print("scored:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査スキーマだけを既存 DB に追加する
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用ファクタ計算例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意点:
- 各処理は DuckDB 接続（kabusys で想定されるスキーマが作成されていること）を前提としています。
- OpenAI 呼び出しは gpt-4o-mini を想定しています。API の課金やレートに注意してください。
- score_news / score_regime は API キーが未設定だと ValueError を投げます。

---

## 実装上の考慮点（抜粋）
- Look-ahead バイアス対策: 多くの関数は date 引数を受け取り、内部で datetime.today() を参照しない設計です。
- 冪等性: ETL の save_* 関数は ON CONFLICT DO UPDATE 等で冪等に保存します。
- レート制御とリトライ: J-Quants クライアントは固定間隔のレートリミッタと指数バックオフを備えています。OpenAI 呼び出し群もリトライ実装が含まれます。
- セキュリティ: ニュース収集は SSRF 対策、defusedxml を利用した XML パース等の対策を行っています。

---

## ディレクトリ構成（主要）
（src/kabusys 以下の主要モジュール）
- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / .env ロード
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py     -- 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      -- RSS ニュース収集
    - quality.py             -- データ品質チェック
    - stats.py               -- zscore_normalize 等
    - audit.py               -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム / ボラティリティ / バリュー
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ はそれぞれ公開 API を __all__ でエクスポート

---

## トラブルシューティング / ヒント
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB のテーブルスキーマは別途スキーマ初期化関数（プロジェクト側で提供される場合）を実行してください。audit.init_audit_db で監査用 DB を簡単に初期化できます。
- OpenAI の JSON Mode を利用しているため、API の出力が厳密な JSON 形式であることが期待されます。応答のパースに失敗した場合はフォールバックとしてスコアを 0 にする等のフェイルセーフが組み込まれています。

---

## 最後に
この README はコードベース（src/kabusys）から抽出した機能説明と利用例です。実運用の前に各種 API キーや DuckDB のテーブルスキーマ、バックテスト用データの準備等を必ず行ってください。さらに詳しい仕様（DataPlatform.md / StrategyModel.md 等のドキュメント）がプロジェクトに含まれている場合はそちらも参照してください。