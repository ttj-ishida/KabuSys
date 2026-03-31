# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリです。J-Quants / kabuステーション / RSS / OpenAI 等と連携して、データの ETL、品質チェック、特徴量計算、ニュース NLP、マーケットレジーム判定、監査ログ管理などを提供します。

---

## 概要

KabuSys は日本株を対象とした研究・運用支援ツール群のコアライブラリです。主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ETL）
- DuckDB をデータ層として用いた永続化・品質チェック・監査ログ
- ニュース（RSS）収集と OpenAI を使った銘柄別 NLP スコアリング
- マーケットレジーム判定（ETF の MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- kabuステーション / Slack 連携のための設定管理や実行モジュール（将来的な発注周りの土台）

設計方針として、ルックアヘッドバイアス防止、冪等性（idempotency）、フェイルセーフ（API失敗時は継続）に配慮しています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルートを検出）
  - 必須環境変数を Settings から取得

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー・株価・財務の差分取得＋品質チェック
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（リフレッシュトークン → id_token）
  - ページネーション・レート制限・自動リトライ
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）

- ニュース収集・処理（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策・サイズ制限・URL 正規化）
  - raw_news / news_symbols への保存ロジック（冪等）

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に保存
  - チャンク・バッチ・リトライ・応答バリデーションを実装

- レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離 + マクロニュースセンチメントを合成して market_regime を更新

- 研究ツール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - 共通統計ユーティリティ（zscore_normalize）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性チェック
  - QualityIssue 型で詳細を返す

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義
  - init_audit_schema / init_audit_db による初期化（UTC タイムスタンプ）

---

## セットアップ手順

前提:
- Python 3.10+ を想定（typing の Optional | annotation を使用）
- 仮想環境の作成を推奨

例（venv + pip）:

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. パッケージインストール
   - プロジェクトがパッケージ化されている前提:
     ```
     pip install -e .
     ```
   - 依存が個別に必要な場合:
     ```
     pip install duckdb openai defusedxml
     ```
   - ログ出力に関しては標準 logging を利用します。必要に応じて structlog 等を追加してください。

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabuステーション API パスワード
     - SLACK_BOT_TOKEN        : Slack Bot トークン
     - SLACK_CHANNEL_ID       : 通知先 Slack チャンネル ID
     - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime 実行時に環境変数として参照）
   - 任意・デフォルト付き:
     - KABUSYS_ENV (development|paper_trading|live) default: development
     - LOG_LEVEL (DEBUG|INFO|...) default: INFO
     - DUCKDB_PATH default: data/kabusys.duckdb
     - SQLITE_PATH default: data/monitoring.db
     - PID_FILE_PATH default: data/execution.pid

   サンプル `.env`（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下はライブラリを使った基本的な操作例です。詳細は各モジュールの docstring を参照してください。

1) DuckDB 接続と ETL（1日分の差分取得・品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP の実行（OpenAI APIキーが環境変数に設定されている想定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

3) レジーム判定（OpenAI キーを引数で渡すことも可）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # 環境変数 OPENAI_API_KEY を使用
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成
```

5) カレンダー・営業日判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を使う設計です。API 呼び出し失敗時はフェイルセーフ（デフォルト値で継続）になるよう実装されています。
- ETL / 保存処理は冪等的（ON CONFLICT DO UPDATE / DO NOTHING）です。
- DuckDB の executemany に空リストを渡すと問題となる箇所に配慮した実装になっています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for NLP) : OpenAI API キー（score_news/score_regime が必要）
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) : SQLite モニタリング DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) : development|paper_trading|live（デフォルト development）
- LOG_LEVEL (任意) : ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します（テスト用途など）。

---

## ディレクトリ構成

（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & 保存ロジック
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult のエクスポート
    - calendar_management.py        — マーケットカレンダー管理 / 営業日判定
    - news_collector.py             — RSS ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー等

各モジュールは docstring に詳細な仕様・設計方針・使用例が記載されています。実装上の挙動（リトライ方針、ルックアヘッドバイアス防止、冪等性等）も注釈として各ファイルにあります。

---

## 運用上の注意

- 本ライブラリはデータ取得・解析の基盤を提供しますが、実際の自動発注（実資金の売買）を行う際は慎重に検証・リスク管理を実装してください。
- OpenAI や外部 API の利用はコストとレート制限があります。プロダクション運用時は適切なレート制御とエラーハンドリングの設定を確認してください。
- 監査ログ（audit）や ETL の保存先（DuckDB）はバックアップ・権限管理を行ってください。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使い自動 env ロードを無効化することができます。OpenAI 呼び出し等はモックしてユニットテストを作成してください。

---

必要に応じて README に具体的なコマンド、CI/CD のセットアップ、Dockerfile、サンプル .env.example を追加できます。どの情報を優先して追記したいか教えてください。