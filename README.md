# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ファクター計算、ニュースの自然言語処理（OpenAI を利用したセンチメント評価）、市場レジーム判定、監査ログ管理などの機能を提供します。

---

## 主な概要

- 名前: KabuSys
- 説明: 日本株のデータパイプライン、リサーチ、AIベースのニュース評価、監査ログ、監視・実行支援を含む自動売買支援ライブラリ
- 目的:
  - J-Quants API からのデータ収集（株価/財務/マーケットカレンダー）
  - DuckDB によるデータ保存と ETL パイプライン
  - ニュースセンチメント（OpenAI）を用いた銘柄別スコアリング
  - ETF（1321）の MA とマクロニュースを合成した市場レジーム判定
  - 監査ログテーブル（発注 → 約定のトレース）管理

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定値の取得（例: JQUANTS_REFRESH_TOKEN）
- データ取得・ETL（kabusys.data.jquants_client, pipeline）
  - J-Quants API からの差分取得（ページネーション対応・レートリミット）
  - raw_prices / raw_financials / market_calendar の保存（冪等）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 次・前営業日の取得 / カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF 対策、raw_news への保存サポート
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄別ニュースセンチメントの算出・ai_scores への保存
  - regime_detector.score_regime: ETF MA とマクロニュース LLM を合成した市場レジーム判定
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン、IC 計算、統計サマリ等
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB の初期化

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の "|" 表記を利用）
- DuckDB、OpenAI SDK、defusedxml 等が必要

例: 仮想環境と必要パッケージ（代表的なもの）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他ユーティリティ: requests 等が必要なら追加
```

推奨: プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。パッケージ化されていれば:
```bash
pip install -e .
```

環境変数:
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD — kabu API（kabuステーション）パスワード
- AI 関連（AI 機能を使う場合）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- 任意
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - その他（PID_FILE_PATH, KILL_FLAG_PATH, 閾値など）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをしません。

例 .env（基本）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要サンプル）

基本的な使い方は DuckDB 接続を作成し、各モジュール関数へ接続と対象日を渡します。

1) 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {num_written} codes")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュース統合）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成されます
```

5) カレンダー更新ジョブを単体で実行
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

6) 設定値にアクセス（コード内で）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

注意点:
- AI 関数は OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。未設定の場合 ValueError を送出します。
- ETL / 保存処理は冪等性（ON CONFLICT）を意識して実装されています。
- 日付の扱いはルックアヘッドバイアスに配慮しており、関数は内部で date.today() に依存しない設計がなされています（target_date を明示することを推奨）。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールとファイル構成の一覧です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメントスコアリング
    - regime_detector.py            — 市場レジーム判定（MA + マクロNLP）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                    — データ品質チェック
    - calendar_management.py        — マーケットカレンダー管理
    - news_collector.py             — RSS ニュース収集
    - audit.py                      — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - monitoring/                      — 監視・実行関連（パス等設定あり）
  - strategy/                        — 戦略関連（シグナル生成等：本リポジトリでは概念的）
  - execution/                       — 発注実行関連（kabu API 連携など：パス提供）

（リポジトリルートに pyproject.toml / .git がある場合、自動的に .env を読み込みます）

---

## 運用上の注意・設計方針

- ルックアヘッドバイアス防止のため、多くの関数は target_date を明示的に受け取り、内部で現在日付を利用しないよう設計されています。
- J-Quants API にはレート制限があり、モジュールは固定間隔のスロットリングを実装しています。
- OpenAI・ネットワーク系はリトライやフォールバック（失敗時は 0.0 など）を備え、ETL やリサーチ処理が一部失敗しても他処理を継続する設計です。
- DuckDB の executemany の挙動（空リストが許容されない等）に配慮した実装になっています。
- RSS 取得には SSRF や XML 攻撃対策（URL スキーマ検証、プライベート IP 検出、defusedxml）を行っています。

---

## さらなる情報

- 詳細な設計や期待されるデータスキーマ（テーブル一覧・カラム）についてはプロジェクトの設計ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください（本 README はコードベースから抽出した主要点の要約です）。
- 実運用での接続先・鍵は必ず安全に管理し、運用環境（paper_trading / live）設定を適切に切り替えてください（settings.env）。

---

必要であれば、README に以下の追加を作成できます：
- requirements.txt 例
- よくあるエラーと対処法（トークン期限切れ、DuckDB スキーマ不足など）
- CI / ローカル起動手順（docker-compose 等）