# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームのコア機能群を提供する Python パッケージです。主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- RSS ニュース収集と OpenAI を利用した銘柄単位の NLP センチメントスコアリング
- ETF を使った市場レジーム判定（MA + マクロニュース）
- 研究向けのファクター計算、将来リターン・IC 等の解析ユーティリティ
- 監査ログ（信号→発注→約定のトレーサビリティ）用スキーマの初期化
- データ品質チェック、マーケットカレンダー管理、ニュース収集の堅牢化

設計上の特徴：
- Look-ahead bias 回避（内部で date.today() を直接参照しない設計）
- DuckDB を中心としたローカル DB 操作（ON CONFLICT ベースの冪等保存）
- OpenAI 呼び出しに対するリトライ / バックオフ / JSON Mode 対応
- 外部接続時の SSRF 防止や受信サイズ制限などセキュリティ考慮

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 各種）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime(conn, target_date, api_key=None) — ETF MA とマクロニュースを組合せて market_regime を書込
- research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings（環境変数管理、.env 自動ロード機能）

---

## 必須環境変数 (.env)

KabuSys は環境変数から設定を読み込みます。プロジェクトルートに `.env` / `.env.local` を置くと自動でロードします（ただしテストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

最低限設定が必要な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY — OpenAI API キー（AI スコアリング用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注など）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

その他のオプション設定（デフォルト値あり）:

- KABUSYS_ENV — one of: development / paper_trading / live （default: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID ファイル（default: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値（%）

.env 例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール（例）:
   - duckdb
   - openai
   - defusedxml
   - その他 network / http 標準ライブラリを利用

例（pip）:
```bash
pip install duckdb openai defusedxml
```

3. リポジトリをクローンし、プロジェクトルートに `.env`（および必要なら `.env.local`）を配置
4. DUCKDB ファイルの親ディレクトリなど必要なディレクトリを作成（通常はコードが自動作成します）
5. 環境変数が正しく設定されていることを確認

注意:
- KabuSys は `.env` 自動読み込みを行いますが、テストや CI で自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な利用例）

以下は代表的な使い方サンプルです。DuckDB 接続は `duckdb.connect(path)` で行います。

1) 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（market_regime へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査 DB 初期化（監査用 DuckDB）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# これで signal_events / order_requests / executions テーブル等が作成されます
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は dict のリスト (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

6) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

API キーを明示的に渡したい関数（テスト用途など）は、`api_key` 引数で渡すことができます（例: score_news(..., api_key="sk-...")）。

---

## 注意点 / 運用上の留意事項

- OpenAI 呼び出しは料金がかかります。実行時は API キーの利用量に注意してください。
- J-Quants API のレート制限や認証に注意（get_id_token 自動リフレッシュ機構あり）。
- ETL / ニュース収集 / OpenAI 呼び出しにはネットワーク I/O が発生します。長時間実行やバッチ運用時は監視を導入してください。
- DuckDB の executemany に空リストを渡すとエラーになる点があり、コードでは予防対応しています。
- モジュールは Look-ahead bias を避ける設計を重視しています。バックテストや研究で使用する場合は DB のタイムライン整合を注意して扱ってください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ情報（__version__）
- config.py — 環境変数 / .env ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（score_news, calc_news_window 他）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save 等）
  - pipeline.py — ETL パイプライン、run_daily_etl 等
  - etl.py — ETL 結果型の再エクスポート
  - news_collector.py — RSS 収集・前処理・保存ロジック
  - calendar_management.py — マーケットカレンダー管理（営業日判定）
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility / Liquidity 計算
  - feature_exploration.py — 将来リターン / IC / summary / rank
- ai、data、research 以下にさらに細かなユーティリティ・ヘルパー関数群あり

---

## テスト / 開発時のヒント

- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml の位置）を基準に行われます。テスト時にローカルで .env を読み込みたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部で小さなラッパー関数を通して行われており、ユニットテスト時に patch / mock がしやすいように設計されています（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- J-Quants の HTTP レイヤも `_request` を通しているため、ネットワーク依存のテストでは urllib/URL opener をモックできます。
- DuckDB を使った関数群は外部アクセスを行わないため、テストは in-memory DuckDB（":memory:"）で行うと簡便です。

---

## ライセンス / コントリビューション

本 README はコードベースのドキュメントであり、実際のライセンス・コントリビューションポリシーはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

---

もし README に追加したい具体的なコマンド例（systemd Unit、cron、Dockerfile、CI ワークフロー等）や、各テーブルのスキーマ一覧（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）を含めたい場合は教えてください。必要に応じてさらに詳細な運用手順やサンプル .env.example を作成します。