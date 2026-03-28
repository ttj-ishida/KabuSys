# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、研究用ユーティリティ、監査ログ（トレーサビリティ）と監視関連の基盤機能を含みます。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants）と DuckDB への冪等保存（差分取得・ON CONFLICT）
- 株価・財務・マーケットカレンダー用の日次 ETL パイプライン（run_daily_etl）
- ニュース収集（RSS）と記事の前処理 / 保存（news_collector）
- OpenAI を使ったニュースセンチメント（score_news）および市場レジーム判定（score_regime）
- 研究向けファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（シグナル → 発注 → 約定のトレーサビリティ）と初期化ユーティリティ
- 設定管理（.env の自動ロード、環境変数アクセス用 Settings）

---

## 必要条件 / 依存関係

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - そのほか標準ライブラリのみで多くを実装していますが、プロジェクトで利用する実行環境に応じて追加が必要になる場合があります。

（プロジェクトには requirements.txt がないため、上の主要ライブラリを環境に入れてください）

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: 仮想環境を作成してアクティベートする
     ```bash
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

2. 依存ライブラリをインストール
   - 例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（パッケージ化されている場合）:
     ```bash
     pip install -e .
     ```

3. 環境変数 (.env) を準備
   - プロジェクトルートに `.env` / `.env.local` を配置すると、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます）。
   - 必須環境変数（少なくともテストや主要機能を実行する場合）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL）
     - KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注実装が使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャネル ID
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
   - オプション:
     - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - 例 (.env)
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要な API とサンプル）

※ すべての操作は DuckDB の接続オブジェクト（duckdb.connect(...) が返す DuckDBPyConnection）を渡して行います。

### 設定にアクセスする
```python
from kabusys.config import settings

print(settings.duckdb_path)       # Path オブジェクト
print(settings.is_live)          # bool
```

### 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl は市場カレンダー、株価、財務データの差分取得と品質チェックを順に行います。
- ETLResult に取得数・保存数・品質問題・エラー概要が含まれます。

### ニュースのセンチメント評価（OpenAI）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {num_written}")
```

- 対象ウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB を参照）です。
- OpenAI の応答は JSON Mode（厳密な JSON）で期待されます。API エラー時は該当コードをスキップして続行します。

### 市場レジーム判定（MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに書き込みます。
- API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用します。

### 監査ログ（Audit DB）初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリは自動作成されます
# テーブルとインデックスが作成され、UTC タイムゾーンがセットされます
```

---

## 設定管理の挙動（.env 自動ロード）

- 起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていない場合、プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env
  - OS の環境変数は保護され、.env で上書きされません。
- .env のパースはシェル風の export KEY=val と引用・エスケープ、インラインコメント等に対応しています。

---

## ディレクトリ構成（主なファイルと説明）

以下はソースツリー（主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / Settings 管理、.env 自動読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py
      - MA200（ETF 1321）とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集・前処理・raw_news への保存、SSRF 対策、XML 安全パース
    - calendar_management.py
      - 市場カレンダー管理、営業日判定ユーティリティ
    - stats.py
      - z-score 正規化等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数
  - research、ai、data 以下にそれぞれ詳細な実装が含まれます。

---

## 注意点・設計上の方針

- Look-ahead バイアス防止: 多くのモジュールで date.today() や datetime.today() を直接参照せず、明示的に target_date を渡す設計になっています。バックテスト・解析での誤用に注意してください。
- 冪等性: J-Quants から保存する際は ON CONFLICT 等を用いて冪等性を担保しています。
- フェイルセーフ: 外部 API（OpenAI/J-Quants）での失敗は可能な範囲でフォールバック（0 やスキップ）して処理継続する設計です。重要なエラーはログに記録されます。
- DuckDB バージョン互換性: 一部 executemany の空リスト等での挙動に注意（コード内で回避処理あり）。

---

## よくある操作例（まとめ）

- ETL を cron / Airflow などで日次実行して DuckDB を最新化
- news_collector で RSS を定期取得 → score_news で AI スコアを付与
- score_regime を実行して当日の市場レジームを保存し、戦略に反映
- init_audit_db で監査 DB を初期化し、戦略 → 発注 → 約定 の監査を採取

---

## 開発・拡張のヒント

- テスト時に .env の自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 呼び出し部は内部でラップされており、ユニットテストでは _call_openai_api をモックすることが想定されています（news_nlp._call_openai_api, regime_detector._call_openai_api を patch）。
- jquants_client では get_id_token を内部キャッシュしており、401 時は自動リフレッシュします。テストでは allow_refresh を制御したり、HTTP レスポンスをモックしてください。

---

必要であれば、README に導入スクリプト例、SQL スキーマ（raw_prices 等）、CI / テスト実行方法や具体的な .env.example を追加します。どの情報をより詳しく追加したいか教えてください。