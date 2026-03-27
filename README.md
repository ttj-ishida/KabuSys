# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
Data ETL、ニュースセンチメント（LLM）評価、マーケットレジーム判定、ファクター研究、品質チェック、監査ログなど、自動売買システムに必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（datetime.now()/date.today() を内部処理で直接参照しない設計）  
- DuckDB を中心としたオンプレミス型データ管理（冪等保存を重視）  
- OpenAI（gpt-4o-mini 等）を使ったニュース分析はフォールバックを用意（API エラー時は安全側の値を使う）  
- ETL / 品質チェック / 監査ログは再現性・トレーサビリティ重視

---

## 機能一覧

- データ取得（J-Quants API）
  - 日次株価（OHLCV）取得 / 保存（fetch_daily_quotes / save_daily_quotes）
  - 財務データ取得 / 保存（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得 / 保存（fetch_market_calendar / save_market_calendar）
  - レート制限・トークン自動更新・リトライ実装

- ETL（差分更新・バックフィル・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP（LLM）
  - RSS 収集（SSRF 対策・gzip/サイズ制限・前処理）
  - ニュースを銘柄ごとに集約 → OpenAI へ送信 → ai_scores へ保存
  - API エラー時のリトライ / フォールバック

- マーケットレジーム判定
  - ETF 1321 の MA200 乖離とマクロセンチメントを合成して日次レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しは安全にリトライ／フォールバック

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB SQL + Python）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化するスキーマを提供
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）

---

## セットアップ手順

前提：
- Python 3.10 以上を推奨（型ヒントに union 型等を使用）
- system-level: ネットワークアクセス（J-Quants / OpenAI）可能な環境

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. インストール
   - pip install -e .            # パッケージを編集可能モードでインストール
   - 必要な外部依存の例：
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. 環境変数 / .env
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます（CWD に依存せず package 内からプロジェクトルートを探索します）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（最低限設定が必要なもの）:
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...         # news_nlp / regime_detector 用（引数でも渡せます）
   - KABU_API_PASSWORD=...      # kabu ステーション API 用
   - KABU_API_BASE_URL=...      # 任意（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb   # デフォルト
   - SQLITE_PATH=data/monitoring.db    # デフォルト
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. データベースディレクトリ作成
   - README で指定した path（例 `data/`）が存在しない場合、自動生成される関数もありますが、事前に作成しておくと安心です。

---

## 使い方（主要な例）

以下は代表的な呼び出し例です。すべて Python スクリプト/REPL から実行できます。

- DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL（株価・財務・カレンダー取得＆品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
# result は ETLResult オブジェクト:
# result.prices_fetched, result.prices_saved, result.quality_issues, result.errors など
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
# APIキーを明示的に渡すことも可能: score_news(conn, date, api_key="sk-...")
```

- マーケットレジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20))
# 成功時は 1 を返します。OpenAI API キーが必要（env か引数で指定）
```

- 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成されます（UTC タイムゾーンに設定）
```

- カレンダー周りユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点：
- OpenAI 呼び出し（news_nlp / regime_detector）は API レート制限・ネットワーク障害を考慮しており、失敗時はフォールバック（スコア 0 など）して処理を継続します。テスト時は内部の _call_openai_api を unittest.mock で差し替えてください。
- DuckDB の executemany に空リストを渡すと一部バージョンでエラーとなるため、関数側でガードしています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール（src/kabusys）を抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / .env 自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュース NLP（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（fetch / save）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETL 結果型の再エクスポート（ETLResult）
    - news_collector.py             # RSS 収集（SSRF 対策・前処理）
    - calendar_management.py        # マーケットカレンダー / 営業日ロジック
    - quality.py                    # データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - audit.py                      # 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            # ファクター計算（momentum/value/volatility）
    - feature_exploration.py        # forward returns / IC / rank / summary
  - research/（上記に含まれる）
  - その他モジュール（strategy / execution / monitoring 等は __all__ に準備）

各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取り、データ永続化や SQL クエリを実行します。

---

## 開発・テスト時のヒント

- .env の自動読み込みは package 内でプロジェクトルート（.git または pyproject.toml）を探索して行います。ユニットテストで明示的に環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワーク I/O はモック可能な内部関数（例: kabusys.ai.news_nlp._call_openai_api や kabusys.data.news_collector._urlopen）を利用しているため、ユニットテストで差し替えてテストを行ってください。
- DuckDB を使った処理はローカルファイル（例 data/kabusys.duckdb）で再現できます。監査ログは別 DB（例 data/audit.duckdb）で分離することを推奨します。

---

## ライセンス・貢献

（このリポジトリにライセンスファイルが含まれている場合はそちらを参照してください。）  
バグ報告や機能追加提案は Issue を立ててください。プルリク歓迎です。

---

以上が KabuSys の概要と基本的な利用手順です。必要であれば README に CI / テスト実行方法、具体的な .env.example や requirements.txt の例、CLI エントリポイント（もしあれば）などを追加できます。追加したい情報があれば教えてください。