# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを含みます。

※ 本リポジトリは src/ 配下にパッケージを配置する典型的な Python プロジェクト構成です。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・保存・品質チェック）
- RSS ニュース収集 & ニュースの NLP（OpenAI を用いたセンチメント）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算 / リサーチ用ユーティリティ
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- 環境変数/設定管理と自動 .env ロード機能

設計上の方針として、バックテストや運用でのルックアヘッドバイアスを避ける実装、冪等性を重視した DB 書き込み、外部 API の堅牢なリトライ/レート制御などを組み込んでいます。

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch/save・レート制御・トークンリフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定 / next/prev/get_trading_days / calendar_update_job）
  - ニュース収集（RSS -> raw_news, SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）

- ai
  - ニュース NLP（gpt-4o-mini を想定した JSON モードでのセンチメント付与）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成）

- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算 / IC / 統計サマリー）

- config
  - 環境変数管理（.env / .env.local の自動ロード、必須変数チェック）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型ヒントの union 表記などを使用）
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを優先してください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

---

## 環境変数

settings（kabusys.config.Settings）で利用される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabuAPI のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の呼び出し時に未指定なら参照）

その他:
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/... デフォルト INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動的に読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: Settings の必須プロパティに未設定でアクセスすると ValueError が発生します。

---

## セットアップ手順（開発環境）

1. リポジトリをクローンしワークスペースへ
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成（.env.example を参照）
   - 必須のキーを設定してください（JQUANTS_REFRESH_TOKEN など）
5. DuckDB 用ディレクトリを作成（必要に応じて）
```bash
mkdir -p data
```

---

## 使い方（簡単なコード例）

- DuckDB に接続して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- news_nlp のスコア付け（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20))  # 環境変数 OPENAI_API_KEY が必要
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB を初期化して接続を得る:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続、監査テーブルが作成済み
```

- 環境設定読み取り:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

テスト時のフック:
- OpenAI 呼び出しはモジュール内の `_call_openai_api` を unittest.mock.patch で差し替えることで外部呼び出しをモックできます（news_nlp と regime_detector は別実装を持ちます）。

---

## よくある操作 / 注意点

- API レート制御やリトライが組み込まれていますが、実運用では J-Quants / OpenAI の利用規約・料金に注意してください。
- run_daily_etl は内部で market_calendar を先に更新し、営業日に調整した上で株価 / 財務を ETL します。
- DuckDB の executemany は空リストを受け取れない箇所に注意（実装で考慮済み）。
- OpenAI のレスポンスが不正/エラーの際はフェイルセーフで 0 相当のスコアにフォールバックする箇所があります（例: macro_sentiment=0.0）。
- .env の自動読み込みはプロジェクトルートを基準とします。CI / テストで不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM によるセンチメント付与（ai_scores へ書込）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save、認証、レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETL の公開 API（ETLResult エクスポート）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py — RSS ニュース収集・前処理・保存
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ / 初期化ユーティリティ
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン/IC/統計サマリー 等

---

## テスト / デバッグのヒント

- OpenAI API 呼び出しはモック可能（モジュール内 `_call_openai_api` を patch）。
- データベースの検証・品質チェックは data.quality の個別関数を呼び出して確認できます。
- ETL の戻り値は ETLResult（to_dict でログ・監査に使いやすい）です。
- カレンダーやニュース取得は外部 API に依存するため、単体テストでは jquants_client や fetch_rss をモックしてください。

---

## まとめ

KabuSys は日本株向けのデータ基盤と研究/自動売買に必要な多数のユーティリティをまとめたライブラリです。  
まずは環境変数を設定し（.env）、DuckDB 接続を用意して run_daily_etl → ai.score_news / regime 判定 を順に実行するワークフローで動作確認してください。

不明点や追加したい使い方（例: CI 用スクリプト、Docker イメージ、具体的な ETL スケジュール例）があればお知らせください。README を補足します。