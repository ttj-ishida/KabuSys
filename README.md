# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（発注・約定トレーサビリティ）、マーケットカレンダー管理などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の研究・自動売買基盤を構築するためのモジュール群です。主な設計方針は以下です。

- Look-ahead バイアスを排除する設計（内部で date.today()/datetime.today() を直接参照しない関数群）
- DuckDB を内部データベースとして使用し、ETL/品質チェック/分析を実行
- J-Quants API からの差分取得（レート制限・リトライ・トークンリフレッシュ対応）
- ニュース収集は RSS ベース、NLP は OpenAI（gpt-4o-mini）を利用して銘柄ごとのスコアを生成
- 監査ログテーブルによりシグナル→発注→約定までのトレーサビリティを保証

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch / save: 株価、財務、上場情報、カレンダー）
  - ETL パイプライン（run_daily_etl、個別 ETL ジョブ）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS から raw_news へ冪等保存、SSRF 対策など）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- ai
  - ニュース NLP（銘柄別センチメントを ai_scores に保存する score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成する score_regime）
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算・IC・統計サマリーなどの特徴量探索ユーティリティ
- config
  - 環境変数 / .env の自動読み込みと Settings オブジェクト

---

## セットアップ手順

前提: Python 3.10+（型注釈で | 型を使用しているため）。必要な Python パッケージは最低限以下を想定しています。

必須パッケージ例:
- duckdb
- openai
- defusedxml

インストール例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時は pip install -e . にする想定
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（settings.jquants_refresh_token で必須）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime 実行時に参照）
- KABU_API_PASSWORD      : kabu ステーション API（必要なら）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合に必要

その他（省略時はデフォルトが使用されます）
- KABUSYS_ENV : development | paper_trading | live （デフォルト development）
- LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` および `.env.local` を自動で読み込みます。
- 読み込みの優先順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで有用）。

例: `.env`（実際の値を設定してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=…
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な API と実行例）

以下はライブラリをインポートして使う簡単な例です。DuckDB の接続は `duckdb.connect(path)` で取得します。

1) 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを生成（OpenAI API 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら環境変数 OPENAI_API_KEY を使用
print(f"written scores: {n_written}")
```

3) 市場レジームスコアの算出（ETF 1321 MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用データベースの初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
```

注意点（よくある失敗）
- OPENAI_API_KEY が未設定のまま score_news / score_regime を呼ぶと ValueError が発生します。
- JQUANTS_REFRESH_TOKEN が未設定だと get_id_token() 等でエラーになります。
- DuckDB のテーブルスキーマは ETL 初期化やマイグレーション処理が必要な場合があります（この README のコードはスキーマ整備関数群を含みます）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の `src/kabusys` 配下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント集約 & OpenAI 呼び出し
  - regime_detector.py  — 市場レジーム判定ロジック
- src/kabusys/data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存）
  - pipeline.py         — ETL パイプライン、run_daily_etl 等
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 収集、SSRF/サイズ対策等
  - calendar_management.py — マーケットカレンダー管理・営業日判定
  - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py            — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py            — 監査ログテーブル初期化（signal_events, order_requests, executions）
- src/kabusys/research/
  - __init__.py
  - factor_research.py        — モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration.py    — 将来リターン計算、IC、統計サマリー
- その他サポートファイル（README.md、pyproject.toml 等を想定）

---

## 実装上の注意 / 設計ポインタ

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml）から読み込まれます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動読み込みを無効化してください。
- OpenAI 呼び出しおよび J-Quants 呼び出しは内部でリトライやバックオフを実装しています。テストでは各モジュールの `_call_openai_api` やネットワーク部分をモックする設計になっています。
- DuckDB を使うことで分析処理を SQL と Python の組合せで効率的に行えます。ETL の保存は冪等（ON CONFLICT DO UPDATE）で実装されています。
- ニュース収集は RSS の XML パースに defusedxml を使用し、SSRF・サイズ攻撃対策を行っています。

---

## トラブルシューティング / FAQ

- エラー: "環境変数 'JQUANTS_REFRESH_TOKEN' が設定されていません。"
  - .env に JQUANTS_REFRESH_TOKEN を追加するか、OS 環境変数として設定してください。
- OpenAI のレート制限や API エラーが出る
  - ライブラリはリトライを行いますが、API キーや使用制限を確認してください。大量バッチ実行は間隔を空けて行ってください。
- DuckDB のスキーマエラー
  - 初期化用関数やスキーマ定義が別ファイルにあることを確認してください（audit.init_audit_schema 等）。

---

この README はコードベースの主要な利用方法・設計意図をまとめたものです。さらに詳細な使い方（例えばスキーマ定義、ETL の cron 設定、監視・通知の設定など）は別途ドキュメント（DataPlatform.md / StrategyModel.md 想定）を参照してください。質問があれば、利用したいワークフロー（ETL の自動化、リアル口座での発注パイプラインなど）を教えてください。より具体的な手順やサンプルを追加します。