# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。ETL、ニュースセンチメント（LLM）による銘柄スコアリング、市場レジーム判定、研究用ファクター計算、監査ログなどのユーティリティを提供します。

主な用途
- J-Quants API からの株価・財務・カレンダー等の ETL
- RSS ニュース収集と OpenAI を用いた銘柄センチメント算出（ai_scores）
- マクロニュース + ETF（1321）MA を組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）
- 発注/約定の監査ログ用スキーマ初期化（DuckDB）

---

## 機能一覧

- 環境設定管理（自動 .env 読込、必須変数チェック）: kabusys.config
- データ ETL（J-Quants クライアント、差分取得、DuckDB 保存）: kabusys.data.pipeline / jquants_client
- 市場カレンダー管理（営業日判定、calendar_update_job）: kabusys.data.calendar_management
- ニュース収集（RSS → raw_news、SSRF 対策、コンテンツ前処理）: kabusys.data.news_collector
- ニュース NLP（OpenAI を用いた銘柄別センチメント）: kabusys.ai.news_nlp
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成）: kabusys.ai.regime_detector
- 研究用モジュール（ファクター計算、特徴量探索、統計ユーティリティ）: kabusys.research, kabusys.data.stats
- データ品質チェック（欠損・スパイク・重複・日付不整合）: kabusys.data.quality
- 監査ログスキーマの初期化 / 専用 DB 作成（order_requests / executions 等）: kabusys.data.audit

---

## 前提 / 必要環境

- Python 3.10 以上（typing の | 演算子等を使用）
- DuckDB
- OpenAI Python SDK（OpenAI API を利用する機能あり）
- defusedxml（RSS パースの安全化）
- （任意）requests 等は不要。標準 urllib を使用しているため追加 HTTP ライブラリは必須ではありませんが、環境に合わせて導入可能です。

推奨インストールパッケージ（requirements.txt の例）
- duckdb
- openai
- defusedxml

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
   - 一般的にはプロジェクトルートが .git または pyproject.toml を含む構成を想定しています（config の自動 .env ロードで参照）。

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install -e .   または必要パッケージを個別にインストール:
     pip install duckdb openai defusedxml

3. 環境変数 / .env を用意
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（kabusys.config）。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env に設定すべき主要キー（例）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxx
- OPENAI_API_KEY=sk-xxxxxxxxxxxx
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=CXXXXXXXX
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development / paper_trading / live
- LOG_LEVEL=INFO

（必要に応じて各自の環境に合わせて調整してください）

4. データディレクトリ作成
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（settings.duckdb_path）
   - 必要に応じてディレクトリを作成: mkdir -p data

---

## 使い方（主要な例）

下記は簡単な使用例です。実運用ではログ設定や例外処理、CI/CD のジョブ化などを行ってください。

- DuckDB 接続の準備（例: ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI を使って銘柄別 ai_scores を書き込む）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースで判定）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  res = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit_duckdb.db")
  # これで signal_events / order_requests / executions テーブル等が作成される
  ```

- market_calendar を更新する夜間ジョブ実行（J-Quants API 必要）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved: {saved}")
  ```

注意:
- OpenAI 呼び出しには API キーが必要です。api_key 引数を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 連携機能は JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token）。
- ETL・ニューススコアリングは大量の API コールや計算を伴うため、ログやレート制限に注意してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携で必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

config.Settings によって必須変数は取得時にチェックされ、不足時は ValueError が発生します。

---

## ディレクトリ構成（主なファイル）

（パッケージのルートは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集（SSRF 対策）
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/ボラ/バリュー等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等
  - (その他) strategy, execution, monitoring パッケージ等のエクスポート（__all__）

---

## 実装上の設計方針（要点）

- ルックアヘッドバイアス対策: 日時の解決で datetime.today()/date.today() を直接参照しない設計（関数に target_date を渡す形を基本とする）。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE 等で再実行可能に設計。
- フェイルセーフ: AI/API エラー時はゼロやスキップで継続する実装箇所がある（例: macro_sentiment=0.0 フォールバック）。
- 秒間レート制御／リトライ: J-Quants のレート制限遵守や OpenAI 呼び出しのリトライ実装を含む。
- セキュリティ: News collector で SSRF 対策・XML 脆弱性対策を実施（defusedxml、ホスト検査、リダイレクト検査）。

---

## よくある運用ヒント

- 本番（live）環境での実行前に KABUSYS_ENV を 'paper_trading' で動作検証すること。
- OpenAI を利用する際はコスト管理（バッチサイズ、トークン削減）を検討してください（news_nlp は銘柄ごと最大文字数とバッチサイズを制限）。
- DuckDB のスキーマ初期化や監査スキーマの作成は一度実行しておくと良いです（kabusys.data.audit.init_audit_db / init_audit_schema）。
- ETL を定期ジョブ化する場合、K-Quants のレート制限とバックフィル方針に注意して schedule を設計してください。

---

## サンプル .env.example

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (任意)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# DB paths
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

README に記載のサンプルはあくまで入門的な使い方です。実運用ではログ設定、例外ハンドリング、運用監視、リトライポリシーやシークレット管理（Vault 等）を適切に行ってください。質問や追加のドキュメント（例えば各テーブルスキーマ、ETL の詳細シーケンス、CI での実行例）が必要であればお知らせください。