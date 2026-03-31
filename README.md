# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、データ収集（ETL）、品質チェック、ニュース NLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部処理で現在時刻を直接参照しない等）
- 冪等性（ETL・保存処理で ON CONFLICT / upsert を利用）
- フェイルセーフ（外部 API 失敗時は部分スキップやデフォルト値で継続）
- DuckDB を主要データストアとして想定

---

## 機能一覧

- data（データプラットフォーム）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day 等）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS の安全な取得・正規化・raw_news 保存）
  - 監査ログ（signal_events / order_requests / executions）と初期化ユーティリティ
  - 汎用統計（Zスコア正規化など）
- ai（ニュース NLP / 市場レジーム判定）
  - gpt-4o-mini を用いたニュースセンチメント解析（stock 単位の ai_score 書き込み）
  - マクロニュース + ETF(1321)のMA乖離を合成した市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライ・フェイルセーフ実装
- research（リサーチ／ファクター）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、統計サマリー
- config（環境・設定管理）
  - .env 自動ロード（プロジェクトルート検出）と Settings API

---

## 必要な依存パッケージ（主なもの）

- Python 3.9+
- duckdb
- openai
- defusedxml

（pip でインストールしてください。環境により追加で標準ライブラリ以外の依存が必要になる場合があります。）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone ...

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトにセットアップ用ファイルがあれば pip install -e . などでインストールしてください）

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただしプロジェクトルートは .git または pyproject.toml を基準に検出）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の主要環境変数（利用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（jquants_client 用）
- OPENAI_API_KEY         — OpenAI API キー（ai.news_nlp / regime_detector 用）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（注文周りがある場合）
- SLACK_BOT_TOKEN        — Slack 通知（ある場合）
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル
- KABUSYS_ENV            — 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL              — ログレベル ("DEBUG","INFO",...)
- DUCKDB_PATH            — デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite 等のパス（例: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（代表的なユースケース）

以下は Python REPL またはスクリプトでの使い方例です。事前に環境変数を設定し、必要なパッケージをインストールしてください。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を省略すると今日（ローカルタイム）を使用
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（AI）で ai_scores を生成する
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合 api_key 引数は不要
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {num_written} ai_scores")
```

3) 市場レジーム判定（1321 MA200 + マクロニュース）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（audit）テーブルを初期化 / 監査 DB を作成する
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
from pathlib import Path

# 監査専用 DB をファイルで作成して接続取得
conn = init_audit_db(Path("data/audit.duckdb"))
# あるいは既存の接続にスキーマ追加だけを行う
# init_audit_schema(existing_conn, transactional=True)
```

5) research モジュールを使ってファクターを計算する
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

ログレベルや KABUSYS_ENV は kabusys.config.settings で参照できます:
```python
from kabusys.config import settings
print(settings.env, settings.is_live, settings.duckdb_path)
```

---

## 開発者向けメモ

- Settings（kabusys.config）:
  - .env 自動ロードの仕組みはプロジェクトルート（.git / pyproject.toml）を基に行われます。テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - サポートされる環境: "development" / "paper_trading" / "live"
  - settings オブジェクト経由で設定値を取得します（例: settings.jquants_refresh_token）

- ETL 周り:
  - run_daily_etl は market_calendar → prices → financials の順で処理し、品質チェックを行います（品質チェックはオプション）。
  - 差分取得ロジック、バックフィル日数、lookahead 日数はパラメータで調整可能です。

- AI 呼び出し:
  - OpenAI の呼び出しは gpt-4o-mini を想定。API 失敗時は指数バックオフとフェイルセーフ（スコアを 0.0）等が組み込まれています。
  - テスト時は内部の _call_openai_api をパッチしてモックできます（各モジュールで別実装となっています）。

- セキュリティ / 安全対策:
  - news_collector は SSRF 対策、gzip サイズチェック、トラッキングパラメータ除去、XML パースに defusedxml を使用する等の防御を含みます。
  - jquants_client はレート制御（120 req/min）とトークン自動リフレッシュ / リトライロジックを備えています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP スコアリング（ai_scores 生成）
  - regime_detector.py               — 市場レジーム判定（1321 MA200 + マクロ）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント + save_* 実装
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETLResult のエクスポート
  - calendar_management.py           — 市場カレンダー管理・判定ロジック
  - stats.py                         — 汎用統計（zscore_normalize）
  - quality.py                       — データ品質チェック（各チェック）
  - news_collector.py                — RSS ニュース収集/前処理
  - audit.py                         — 監査ログ DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py               — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py           — 将来リターン・IC・統計サマリー等
- monitoring/ (パッケージ参照あり: sqlite などモニタリング周りが想定)
- execution/ (発注/約定関連モジュール想定)
- strategy/ (戦略層想定)

（実装ファイルやサブモジュールは上記以外にも含まれる可能性があります。README が扱っているのはコードベースの主要モジュールです。）

---

## 注意事項 / ベストプラクティス

- 本ライブラリの AI 部分や J-Quants API 呼び出しは有料 API を利用する可能性があるため、キーの管理や実行コストに注意してください。
- 本番口座での自動売買を行う場合は、必ず paper_trading（または検証環境）で十分に検証してください。settings.is_live フラグで live 環境を判定できます。
- DuckDB のスキーマやテーブル（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, news_symbols 等）は ETL 実行前に用意されている前提です。スキーマ初期化は別途 schema 初期化用スクリプトを用意することを推奨します。
- ETL / API 呼び出し時のログは運用上重要です。LOG_LEVEL を適切に設定し、ログの保管や Slack 等への通知実装を検討してください。

---

必要に応じて README 内容にサンプル .env.example、スキーマ初期化手順、運用ジョブ（cron/airflow）のサンプルを追加できます。追加したい情報や、特定の使い方（例: バックテスト連携、kabuステーション発注フロー）を教えてください。