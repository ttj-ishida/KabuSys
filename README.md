# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の高レベル機能を備えています。

- J-Quants API を用いた株価・財務・カレンダーの差分取得（ETL）
- DuckDB をデータ層に使った冪等保存（ON CONFLICT を利用）
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（銘柄別・マクロ）
- 市場レジーム判定（ETF の MA200 乖離 + マクロセンチメント）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution の完全トレーサビリティ）

設計上の方針として、バックテストでのルックアヘッドバイアスを避けるために
内部ロジックは日付引数を明示的に受け取り、datetime.today()/date.today() を直接参照しない実装が多く採られています。

---

## 特長（機能一覧）

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
  - J-Quants のレート制限とリトライを考慮したクライアント
- ニュース収集
  - RSS フィードの取得・前処理・ID 正規化・raw_news への冪等保存
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去
- NLP / LLM
  - news_nlp.score_news: 銘柄ごとのニュース統合センチメント生成（バッチ・JSON Mode）
  - regime_detector.score_regime: ETF（1321）MA200乖離とマクロセンチメントを合成して市場レジーム判定
  - OpenAI API 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 にフォールバック）
- Research
  - calc_momentum / calc_volatility / calc_value（prices_daily/raw_financials に基づくファクター）
  - calc_forward_returns / calc_ic / factor_summary / rank（ファクター評価支援）
- Data utilities
  - calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
  - data.quality: 欠損、スパイク、重複、日付不整合チェック
  - data.audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- 設定管理
  - kabusys.config.settings: .env 自動読み込み（プロジェクトルート基準）と環境変数管理

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらに従ってください）

---

## インストール

開発中にローカルで使う場合の一例:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージと依存をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクト配布パッケージがある場合）pip install -e .

---

## 環境設定 (.env)

kabusys.config.Settings が参照する主な環境変数:

必須（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知に利用する場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- OPENAI_API_KEY — OpenAI 呼び出しで使用（news / regime modules は引数でも指定可能）

自動 .env ロード:
- パッケージは、パッケージファイル位置から上位ディレクトリを探索して
  `.git` または `pyproject.toml` を見つけたディレクトリをプロジェクトルートと判断し、
  その `.env` と `.env.local` を自動的に読み込みます（OS 環境変数優先）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## クイックスタート（使い方）

下記は基本的な利用例です。DuckDB 接続オブジェクト（duckdb.connect）を渡して関数を実行します。

1) ETL（日次 ETL の実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコア付与（銘柄別）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key は不要
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / executions などにアクセスできます
```

5) リサーチ用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors: list[dict] に (date, code, mom_1m, mom_3m, mom_6m, ma200_dev) が含まれます
```

注意点:
- LLM 呼び出し（news_nlp, regime_detector）は OpenAI API キーが必要です。関数引数で api_key を渡すか環境変数 OPENAI_API_KEY をセットしてください。
- ETL / API クライアント (J-Quants) はネットワークアクセスと API キー（JQUANTS_REFRESH_TOKEN）が必要です。
- 関数はエラー時にログ出力や部分的なフォールバックを行う設計です（例: LLM 呼び出しに失敗した場合はセンチメント 0 を使う等）。

---

## 主要なディレクトリ構成

（src/kabusys 以下の主なファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースのセンチメント処理（銘柄別バッチ、OpenAI 呼出）
    - regime_detector.py — 市場レジーム判定（ETF 1321 MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・raw_news への保存
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 運用上の注意 / ベストプラクティス

- 環境は KABUSYS_ENV によって切り替えられます（development/paper_trading/live）。live 環境ではより厳格なログ・リスク管理が要求されます。
- DuckDB ファイルはバックアップと権限管理を適切に行ってください。
- OpenAI の API 利用はコストが発生します。バッチサイズやチャンク設定（news_nlp の _BATCH_SIZE 等）を運用状況に合わせて調整してください。
- ETL は差分取得を行いますが、初期ロードや大きなリフェッチ時はバックフィル日に注意してください（pipeline.run_daily_etl の backfill_days 等）。
- .env.local を用いてローカルでの上書きを行えます。OS 環境変数は常に優先されます。

---

## 貢献 / テスト

- モジュール内の API コールやネットワークを行う関数はモック可能な形で設計されています（テスト時は _call_openai_api や _urlopen を patch する等）。
- 自動ロードされる .env の動作を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時に有用です）。

---

もし README に追加したい具体的なサンプルや運用手順（CI 設定、デプロイ手順、Docker イメージ例など）があれば教えてください。必要に応じて追記・展開します。