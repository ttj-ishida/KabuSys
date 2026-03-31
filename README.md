# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼研究・自動売買基盤のコアライブラリです。J-Quants からのデータ取得・ETL、ニュース収集と LLM を使ったニュースセンチメント、ファクター計算・特徴量探索、監査ログ（トレーサビリティ）、市場カレンダー管理、そして発注監視のためのユーティリティ群を提供します。

主な設計方針は「Look‑ahead バイアス回避」「冪等性」「堅牢な API リトライとレート制御」「DB（DuckDB）を中核にしたオフライン解析」です。

---

## 機能一覧

- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ニュース収集
  - RSS フィード取得、前処理、記事IDの正規化（SHA-256）、SSRF 対策、サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄別ニュースのセンチメントを LLM（gpt-4o-mini）で算出し ai_scores テーブルへ保存
  - マクロニュースを使った市場レジーム判定（ma200 と LLM の重み合成）
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合の検出
- マーケットカレンダー管理
  - market_calendar の夜間更新ジョブと営業日判定ヘルパー（next/prev/get）
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ初期化とユーティリティ
  - 監査・トレーサビリティのための冪等性設計
- 環境管理
  - .env ファイルまたは環境変数からの設定読み込み（自動読み込み・保護機能あり）

---

## 必要要件（推奨）

- Python 3.9+
- 主要依存（一例）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

（パッケージ化時に requirements.txt / pyproject.toml を参照してください）

---

## 環境変数（主な必須 / 任意）

このライブラリは環境変数から設定を読み取ります。自動的にプロジェクトルートの`.env` → `.env.local`（`.env.local`が上書き）を読み込みます（OS 環境変数が最優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings.require により未設定時は例外）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（利用する場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

推奨 / 任意:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用途）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例: .env.example（README 用サンプル）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. インストール
   - ローカル開発インストール（パッケージ化されている場合）:
     ```
     pip install -e .
     ```
   - 必要なライブラリを個別にインストールする場合:
     ```
     pip install duckdb openai defusedxml
     ```
   - 追加でテスト用ツールや linter を導入する場合は適宜 requirements を参照してください。

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、システム環境変数として設定してください。
   - 自動読み込みを一時的に止めたい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主要なユースケース）

以下は実用的な Python スニペット例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))

# 結果の確認
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム（ma200 + マクロニュース）を判定して market_regime に保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用の DuckDB を初期化して接続を取得する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブル定義・インデックスを作成します（UTC タイムゾーンを設定）
```

- RSS フィードを取得する（ニュース収集テスト）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants の ID トークンを取得（内部は settings.jquants_refresh_token を利用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
print(token)
```

注意:
- AI 関連関数（score_news, score_regime）は OpenAI API を呼び出すため料金が発生します。テストでは API 呼び出し箇所をモックすることを推奨します。
- データ取得や DB 書き込みは冪等設計になっていますが、本番環境での操作はバックアップ等運用手順を整えてから行ってください。

---

## 典型的なワークフロー例

1. 毎日深夜に run_daily_etl をスケジュールして raw_prices / raw_financials / market_calendar を最新化
2. ETL 後に品質チェック（quality.run_all_checks）で問題検出
3. morning バッチで research のファクターを再計算 → 信号生成（戦略）
4. 戦略のシグナルを order_requests に書き出し、実際の発注・約定を監査テーブルで追跡
5. ニュースが入るたびにニュース収集・AI スコアリングで ai_scores を更新し、短期リスク管理に反映

---

## ディレクトリ構成

主要ファイル・モジュールのツリー（src/kabusys）と簡単な説明:

- src/kabusys/
  - __init__.py — パッケージ公開（version: 0.1.0）
  - config.py — 環境設定の読み込み・検証（.env 自動ロード、Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄別ニュースセンチメント算出（OpenAI 呼び出し、チャンク・リトライ）
    - regime_detector.py — ma200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック、リトライ、レート制御）
    - pipeline.py — ETL のエントリポイント（run_daily_etl など）
    - etl.py — ETL 用の公開型（ETLResult）
    - news_collector.py — RSS 取得・前処理・保存ロジック（SSRF 対策・XML 安全処理）
    - calendar_management.py — market_calendar 管理と営業日ヘルパー
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
    - stats.py — z-score 正規化などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - ai、data、research 以下に細かい実装があります（上記は主要ファイル）

---

## テストとモックについて

- 外部 API（OpenAI, J-Quants, RSS）を呼び出す箇所は明確に分離されており、ユニットテスト時はそれらの呼び出し（HTTP 層や _call_openai_api、_urlopen、jquants_client._request など）をモックしてください。
- news_nlp と regime_detector はそれぞれ専用の内部 API 呼び出しポイントを持つため、個別に差し替え可能です。

---

## 運用上の注意

- OPENAI_API_KEY や J-Quants のリフレッシュトークンは機密情報です。リポジトリにハードコードしないでください。
- run_daily_etl などは大量のデータ操作を伴います。実運用ではジョブのロギング・監視・エラーハンドリングを整備してください。
- DuckDB のファイルパスはバックアップと一貫性のため分離して運用することを推奨します。

---

必要があれば、README にさらに詳しい API リファレンス（各関数の引数/戻り値/例外）や運用手順（cron/airflow のジョブ例、Slack 通知連携例）を追記します。どの部分の詳細を追加しますか？