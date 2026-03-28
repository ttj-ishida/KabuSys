# KabuSys — 日本株自動売買システム

簡潔な日本語 README（README.md）です。プロジェクトの目的、主な機能、セットアップ・使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。  
主に以下を提供します：

- J-Quants API を用いたデータ ETL（株価、財務、JPX カレンダー）
- ニュースの NLP（LLM）による銘柄センチメント算出
- 市場レジーム判定（ETF とマクロニュースを組み合わせる）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック・マーケットカレンダー管理
- 監査用テーブル（シグナル→発注→約定のトレーサビリティ）
- 冪等性・リトライ・レート制御を考慮した実装

設計上の特徴：
- Look-ahead バイアスを避けるため、内部で date.today()/datetime.today() を（ほとんど）参照しないよう実装
- DuckDB を主要なローカル分析 DB として使用
- OpenAI（gpt-4o-mini）を用いた JSON Mode での NLP スコアリング（news_nlp / regime_detector）
- J-Quants API 呼び出しはレートリミット制御とリトライあり

---

## 主な機能一覧

- data/
  - ETL（daily ETL: 株価・財務・カレンダーの差分取得・保存）
  - J-Quants クライアント（認証、分页、保存関数）
  - news_collector（RSS 収集、SSRF 対策、前処理）
  - quality（データ品質チェック：欠損・重複・スパイク・日付不整合）
  - calendar_management（営業日判定、next/prev_trading_day 等）
  - audit（監査テーブル定義・初期化）
  - stats（z-score 正規化）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを LLM でスコアして ai_scores に書込
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF とマクロニュースで市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件（例）

- Python 3.10+
- 主要依存パッケージ（例、プロジェクトに合わせて適切に管理してください）
  - duckdb
  - openai
  - defusedxml
- ネットワーク通信（J-Quants, RSS, OpenAI）にアクセス可能な環境

（実際のパッケージバージョンはプロジェクトの pyproject.toml / requirements.txt に合わせてください）

---

## 環境変数（必須／任意）

必須（Settings が _require するもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN — Slack 通知ボットのトークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルトあり:
- KABUSYS_ENV — `development`, `paper_trading`, `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG`/`INFO`/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動ロードを無効化
- OPENAI_API_KEY — OpenAI API キー（ai.score_* 呼び出しで引数に渡さない場合に使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使う SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）

自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env`（優先度低）と `.env.local`（優先度高）を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env ファイルの例（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
```

---

## セットアップ手順（開発向けの一例）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （またはプロジェクトの requirements.txt / pyproject.toml に従う）

4. 環境変数を設定
   - `.env` または `.env.local` をプロジェクトルートに作成するか、OS 環境変数を設定

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単なコード例）

前提: DuckDB に接続できる状態、必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定済み。

- DuckDB 接続の例（ローカルファイル）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（全体パイプライン）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 今日（または任意の日付）を指定して実行
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP スコアを生成して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジームを算出して market_regime テーブルに書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化（監査テーブルの作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_kabusys.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- J-Quants の ID トークンを明示的に取得する
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # JQUANTS_REFRESH_TOKEN を使って取得
```

注意点:
- OpenAI 呼び出しは課金対象・レート制限対象です。テスト時は library 内の _call_openai_api をモックして呼び出しを無効化してください（コードにその旨の注記あり）。
- ETL / API 呼び出しはリトライやレート制御が入っていますが、ネットワークや API の利用制限に注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュール構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py (ETL の公開)
    - pipeline.py (日次 ETL 実装)
    - stats.py
    - quality.py
    - audit.py (監査テーブル定義・初期化)
    - jquants_client.py (J-Quants API クライアント)
    - news_collector.py (RSS 収集)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

主要な公開 API と用途（例）
- kabusys.config.settings — 環境変数／設定アクセス
- kabusys.data.pipeline.run_daily_etl — 日次 ETL（全体）
- kabusys.ai.news_nlp.score_news — ニュース NLP スコアリング
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査 DB 初期化
- kabusys.research.* — 研究用ファクター計算・評価

---

## 実装上の注意／設計メモ

- Look-ahead バイアス防止のため、バックテストやスコアリング関数は内部で現在時刻を直接参照しないよう配慮されています（関数呼び出し側で target_date を明示してください）。
- J-Quants クライアントは内部で固定間隔スロットリング（120 req/min）と指数バックオフを実装しています。
- news_collector は SSRF 対策、XML 脅威対策（defusedxml）、レスポンスサイズ上限を実装しています。
- ai モジュールは OpenAI の JSON Mode を使い、レスポンスを厳密にパース・バリデーションします。API エラー時はフェイルセーフ（スコア 0.0 またはスキップ）で継続する設計です。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT 等）になるよう実装されています。

---

## テスト・デバッグ時のヒント

- 環境変数自動ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- OpenAI／J-Quants 呼び出しはユニットテストでモックし、外部依存を切り離すことを推奨
- DuckDB は ":memory:" を使ってインメモリ DB でテスト実行可能（audit.init_audit_db 等）

---

この README はコードベースの主要な使い方と設計方針を短くまとめたものです。詳細は各モジュールの docstring を参照してください。開発者向けの運用手順（デプロイ、CI、バックテストワークフロー等）は別途ドキュメント化することを推奨します。