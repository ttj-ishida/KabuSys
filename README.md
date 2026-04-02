# KabuSys

日本株向けのデータ基盤・研究・自動売買ユーティリティ群です。  
DuckDB を中心としたデータ ETL、ニュース収集・NLP（OpenAI 利用）、市場レジーム判定、ファクター計算・特徴量解析、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な用途
- J-Quants API からの株価 / 財務 / カレンダーの差分 ETL
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメントスコアリング
- ETF の移動平均とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）とリサーチユーティリティ
- 監査用テーブルの初期化、発注・約定のトレース（audit）
- データ品質チェック（欠損・重複・スパイク・日付整合性）

---

## 機能一覧（抜粋）

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証・リトライ・レート制御）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF やサイズ制限、トラッキングパラメータ除去）
  - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - 統計ユーティリティ（zscore_normalize）
  - 監査ログのスキーマ初期化（init_audit_schema / init_audit_db）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、ランク化ユーティリティ

---

## セットアップ

前提
- Python 3.10+ を推奨
- DuckDB, OpenAI SDK, defusedxml 等が必要

インストール例（簡易）
1. 仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb openai defusedxml

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数 / .env
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にする場合は環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（必須/任意）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（ai モジュールを使う場合は必須）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視用設定
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / ...（デフォルト INFO）

ヒント: .env.example（プロジェクトにある想定）をコピーして `.env` を作成してください。

---

## 使い方（基本例）

1) DuckDB 接続の用意と監査テーブル初期化
```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db, init_audit_schema

# ファイル DB を使う例
conn = duckdb.connect(str(settings.duckdb_path))
# 既存接続に監査スキーマを追加する場合:
init_audit_schema(conn)
# 監査専用ファイルを作る場合:
# conn2 = init_audit_db("data/audit.duckdb")
```

2) 日次 ETL 実行（J-Quants から株価/財務/カレンダーを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントのスコア付け
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API key を環境変数 OPENAI_API_KEY でセットしておくか、api_key 引数を渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

4) 市場レジームの判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ユーティリティ例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

---

## 自動環境読み込みの挙動

- ロード優先度: OS 環境変数 > .env.local > .env
- プロジェクトルートの判定はこのパッケージ内のファイルパスを起点として行うため、CWD に依存せず配布後も動作します。
- テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの集約と OpenAI によるセンチメント、ai_scores への書き込み
    - regime_detector.py — ETF MA200 とマクロニュースを合成して market_regime に書き込み
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、取得・保存ロジック（rate limit, retry, token refresh）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・正規化・保存（SSRF 対策、サイズ制限）
    - calendar_management.py — 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査用テーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム／ボラティリティ／バリュー等の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank 等

---

## 注意事項 / 設計方針（重要な点）

- ルックアヘッドバイアスの排除を重視:
  - AI スコアやレジーム判定、ETL は target_date ベースで過去データのみを参照するよう設計されています（date.today() を直接参照しない箇所が多い）。
- OpenAI 呼び出しは JSON Mode を使用し、レスポンス検証・リトライロジックが組み込まれています。API 失敗時はフェイルセーフ（0.0 等）で継続する設計です。
- J-Quants クライアントはレート制限とトークン自動リフレッシュ、ページネーション対応、取得時刻（fetched_at）の記録を行います。
- DuckDB に対しては可能な限り冪等操作（ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT）を用いて安全に保存します。
- news_collector は SSRF、XML Bomb、レスポンスサイズ制限などセキュリティ対策を含みます。

---

## よくある操作まとめ

- ETL 実行: kabusys.data.pipeline.run_daily_etl
- ニューススコア取得: kabusys.ai.news_nlp.score_news
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 監査DB初期化: kabusys.data.audit.init_audit_db / init_audit_schema
- カレンダー更新ジョブ: kabusys.data.calendar_management.calendar_update_job

---

## 開発 / テストについて

- 自動環境読み込みを切る: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部 API はテスト時にモック可能（ソース内にモック想定の箇所あり）
- DuckDB を ":memory:" で初期化して単体テストを行えます

---

この README はコードベースの説明の要約です。より詳細な設計意図や API 仕様は各モジュールの docstring を参照してください。必要であれば、インストールの詳細な手順や運用手順（データ初期化スクリプト、cron 化例、監視構成など）を追加で作成します。希望があれば教えてください。