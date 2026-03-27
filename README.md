# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB を用いたデータ ETL、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）や市場カレンダー管理など、売買戦略基盤で必要となる機能群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() や datetime.now() に依存しない処理設計）
- DuckDB を中心に SQL＋Python で効率的にデータ処理
- 外部 API呼び出し（J-Quants / OpenAI 等）にはレート制御とリトライを実装
- 冪等性を考慮した DB 保存（ON CONFLICT DO UPDATE 等）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml で探索）
  - 必須環境変数取得ユーティリティ（settings）
- データ ETL（J-Quants）
  - 株価日足（raw_prices / raw_prices 保存）
  - 財務データ（raw_financials）
  - JPX 市場カレンダー（market_calendar）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL run_daily_etl
- ニュース収集
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores へ書き込む score_news
  - マクロニュースと ETF (1321) の MA200 乖離を合成して市場レジーム判定 score_regime
  - gpt-4o-mini の JSON Mode を利用、429/5xx 等のリトライ実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン / IC / 統計サマリー（calc_forward_returns / calc_ic / factor_summary）
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue 型で収集）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルの初期化・ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（`|` 型ヒントを利用しているため）
- Git（.env 自動読み込みのプロジェクトルート探索に利用される場合あり）

1. リポジトリをクローン / 取得
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 本コードベースで使われている外部ライブラリの例：
     - duckdb
     - openai
     - defusedxml
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発用に setuptools 等が必要であれば適宜インストールしてください。

4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を作成すると自動で読み込まれます（.env.local は .env の上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 主要な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 実行時に指定可能）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必要に応じて）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite パス（監視用 DB、デフォルト: data/monitoring.db）
   - KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト: development）
   - LOG_LEVEL : "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な関数例）

以下は簡単な Python スニペット例です。実際はロギングやエラーハンドリングを追加してください。

- 設定取得
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続と ETL（日次）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
print(result.to_dict())
```

- ニュースセンチメントスコア（OpenAI API 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルへ書き込み/クエリが可能
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点：
- OpenAI を使う関数は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。未指定だと例外になります。
- J-Quants 呼び出しは settings.jquants_refresh_token を用いて id_token を取得します（get_id_token などで利用）。

---

## 重要な挙動・運用メモ

- .env 自動読み込み
  - パッケージ import 時にプロジェクトルートを探索して `.env` と `.env.local` を読み込みます（OS 環境変数優先、.env.local は .env を上書き）。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

- 環境（KABUSYS_ENV）
  - 有効値: development / paper_trading / live
  - settings.is_live / is_paper / is_dev メソッドで簡単に判定できます。

- レート制御 / リトライ
  - J-Quants クライアントは 120 req/min のレート制限に合わせた固定間隔スロットリングとリトライを実装しています。
  - OpenAI 呼び出しも 429・タイムアウト・5xx に対するリトライあり。

- ルックアヘッドバイアス防止
  - 日次処理やニューススコアリング等は target_date を明示して実行する設計（内部で date.today() に依存しない）。バックテスト等での使用は特に注意してください。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要ファイル構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュース NLP（score_news）
    - regime_detector.py                # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント・保存ロジック
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - etl.py                            # ETL インターフェース再エクスポート
    - news_collector.py                 # RSS 収集・保存
    - calendar_management.py            # 市場カレンダー管理
    - quality.py                         # データ品質チェック
    - stats.py                           # 汎用統計ユーティリティ
    - audit.py                           # 監査ログ初期化・ヘルパー
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算
    - feature_exploration.py            # 将来リターン / IC / サマリー

（この README はコードベースの一部モジュールを元に要約しています。実際のリポジトリには追加のモジュール・ユーティリティが含まれる可能性があります。）

---

## 貢献 / テスト

- コードの追加・変更を行う場合は、既存の設計方針（ルックアヘッドバイアス回避、冪等性、DB トランザクション管理）に従ってください。
- 外部 API を使うロジックは必ずモック可能にしてユニットテストを用意してください（例: _call_openai_api をパッチする等）。

---

ご不明点や特定機能の詳しい使い方（例えば ETL のパラメータ調整やニュース収集ソースの追加、監査テーブルの拡張など）が必要であれば、用途に合わせた利用例を追記します。