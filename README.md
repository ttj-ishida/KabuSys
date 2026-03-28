# KabuSys

バージョン: 0.1.0

日本株のデータ収集・品質管理・リサーチ・AIベースのニュース分析・市場レジーム判定・監査ログ（トレーサビリティ）までを包含する自動売買 / データプラットフォーム用ライブラリ。

主な設計思想：
- DuckDB を中心とするローカルデータレイク
- J-Quants API からの差分ETL（レート制御・リトライ・トークン自動更新）
- ニュースは RSS 収集 → LLM（OpenAI）で銘柄別センチメント付与（JSON Mode）
- Market レジーム判定で MA200 とマクロニュースセンチメントを組合せ
- ETL と品質チェックは Look-ahead バイアスを避ける設計
- 監査ログ（signal → order_request → execution）で発注フローの完全トレーサビリティ

---

## 機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数の必須チェック（settings オブジェクト）

- データ収集（J-Quants クライアント）
  - 株価日足（OHLCV）取得・保存（ページネーション・レート制御・リトライ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 上場銘柄情報取得

- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 差分取得、バックフィル、品質チェックの実装

- データ品質チェック
  - 欠損データ検出（OHLC）
  - 前日比スパイク検出
  - 主キー重複検出
  - 日付不整合（未来データ、非営業日データ）検出

- ニュース収集 / NLP
  - RSS 収集（トラッキングパラメータ削除、SSRF 対策、サイズ制限）
  - OpenAI を用いた銘柄別センチメント算出（バッチ、リトライ、JSON 検証）
  - ニュースウィンドウの計算（JST基準）

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成し、bull/neutral/bear を判定

- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化

- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化

---

## セットアップ手順（開発用）

注意: このリポジトリは外部パッケージ（duckdb, openai, defusedxml など）に依存します。requirements.txt がない場合は以下を参考にしてください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（参考）
   ```
   pip install duckdb openai defusedxml
   # 追加推奨: requests (必要なら), pytest（テスト実行用）
   ```

   プロジェクトを editable install する場合:
   ```
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動読み込みされます（README のサンプル .env を参考に作成してください）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須の環境変数（実行コンテキストにより必要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI（news_nlp / regime_detector で利用）
- （任意）DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

設定オプション:
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## 使い方（簡易ガイド）

以下は Python REPL / スクリプトからの簡単な利用例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

- 設定を確認する
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.log_level)
```

- DuckDB 接続を開く（デフォルトパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメント (ai.news_nlp.score_news)
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY で渡すか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定 (ai.regime_detector.score_regime)
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成される
```

- RSS フェッチ（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しは API レート・料金が発生します。テストではモックを利用してください。
- jquants_client の API 呼び出しはレート制御とリトライを持ちますが、トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- ETL / スコアリングは Look-ahead バイアスを避けるよう設計されています（target_date 未満、ウィンドウ定義など）。

---

## .env 自動読み込みの挙動

- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードはプロジェクトルート検出により行われる（.git または pyproject.toml を上位に持つディレクトリがルート）。
- テストや特別な用途で自動ロードを無効にするには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env の解析はシェル風の export KEY=val、クォート、行末コメントなどに対応しています。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル / モジュールの一覧（src/kabusys 以下）。実際のリポジトリに合わせて調整してください。

- src/kabusys/
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
    - stats.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（その他ファイル）
  - ai/...（上記）

主要なモジュールの役割:
- kabusys.config: 環境設定および .env 自動読み込み
- kabusys.data.jquants_client: J-Quants API クライアント + DuckDB 保存ユーティリティ
- kabusys.data.pipeline: 日次 ETL の統合エントリポイント
- kabusys.data.news_collector: RSS 取得と前処理（SSRF対策等）
- kabusys.ai.news_nlp: ニュースの銘柄別センチメント算出
- kabusys.ai.regime_detector: 市場レジーム判定
- kabusys.research: ファクター計算・探索モジュール
- kabusys.data.audit: 発注フローの監査ログテーブル定義と初期化

---

## 運用上の注意 / ベストプラクティス

- API キーやトークンは機密情報です。`.env` をリポジトリにコミットしないでください。
- OpenAI / J-Quants の呼び出しはコスト・レート制限があるため、バッチ処理・キャッシュを検討してください。
- テスト時は外部API呼び出しをモックしてください（news_nlp._call_openai_api 等はパッチして差し替えられる設計）。
- DuckDB のスキーマとデータは本番とテストで分離してください（別ファイルパス）。
- ETL 実行ログは必ず確認し、run_daily_etl の ETLResult を監視して品質問題を検出してください。

---

もし README のサンプル .env や requirements.txt、簡単な起動スクリプト（systemd / cron 用）が必要であれば、用途に合わせてテンプレートを作成します。どの部分を優先して追加したいか教えてください。