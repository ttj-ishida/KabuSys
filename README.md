# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、マーケットカレンダー管理、ファクター計算、監査ログ（オーダー・約定のトレーサビリティ）など、取引戦略開発と運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能一覧

- データ取得・ETL
  - J-Quants API からの株価（日足）・財務データ・マーケットカレンダー取得（ページネーション対応、リトライ・レート制御付き）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質管理
  - 欠損データ、重複、スパイク（急騰・急落）、日付整合性チェック（quality.run_all_checks）

- カレンダー管理
  - JPX カレンダーの差分更新、営業日判定、前後営業日の取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - 夜間バッチ更新ジョブ（calendar_update_job）

- ニュース収集 / NLP
  - RSS 取得（SSRF/大容量対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - マクロニュース + ETF（1321）MA200乖離を合成した市場レジーム判定（ai.regime_detector.score_regime）

- 研究用ユーティリティ
  - ファクター（モメンタム / ボラティリティ / バリュー）計算（research.factor_research）
  - 将来リターン計算・IC（rank, calc_forward_returns, calc_ic 等）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルのスキーマ初期化（init_audit_schema / init_audit_db）
  - 発注・約定の監査記録を時間軸で辿れる仕組み

- 環境設定管理
  - .env / .env.local の自動読み込み機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で設定にアクセス（kabusys.config.settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（コードは | 型記法を使用）
- DuckDB を利用（pip で duckdb をインストール）
- OpenAI SDK（openai）を利用
- defusedxml（RSS パーサ保護）など

推奨依存ライブラリ（参考）
- duckdb
- openai
- defusedxml

例: venv を作ってインストールする場合
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
# 開発用途ならパッケージを editable インストール
pip install -e .
```

.env の準備:
- プロジェクトルート（pyproject.toml または .git がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先される）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須／推奨の環境変数（概要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（運用時）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token（運用時）
- SLACK_CHANNEL_ID: Slack チャンネル ID（運用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視関連設定
- KABUSYS_ENV: environment ('development'|'paper_trading'|'live')（デフォルト: development）
- LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト: INFO）

例 .env の一部:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your-password
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なエントリ / サンプル）

基本的に DuckDB 接続を渡して利用します。以下は利用例です。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）をスコアリングする
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY が設定されていれば api_key は不要
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 の MA200 + マクロニュース）を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイルパス（:memory: でインメモリ DB も可能）
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログに書き込めます
```

5) J-Quants の ID トークン取得 / 直接 API 呼び出し
```python
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使用
records = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

6) データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- news_nlp / regime_detector は OpenAI を呼び出します。API キーは引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- すべての関数は基本的にルックアヘッドバイアスを避けるよう設計されており、内部で date.today() を直接参照しないものが多いです（target_date を明示的に与えることを推奨します）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、内部で注意して扱っています（呼び出し側は通常意識不要）。

---

## ディレクトリ構成

（抜粋。主要モジュールのみ記載）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理 (settings)
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（銘柄別）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py             — ETL パイプライン / run_daily_etl 等
    - etl.py                  — ETLResult 再エクスポート
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py       — RSS 取得 / 前処理 / 保存用ユーティリティ
    - calendar_management.py  — マーケットカレンダー管理・営業日判定
    - audit.py                — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー等

---

## 開発 / テストについて（補足）

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。テスト時に自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しなど外部 API はモック可能な設計です。内部の _call_openai_api 関数等はユニットテストで差し替えられるようになっています。
- DuckDB 接続はファイルパス（例: data/kabusys.duckdb）または ":memory:" を使えます。

---

## ライセンス・貢献

（このテンプレートには記載がありません。実プロジェクトでは LICENSE ファイルを追加してください。）

---

README は以上です。必要があれば以下を追加できます:
- 具体的な .env.example の全環境変数一覧（詳しい説明付き）
- requirements.txt の推奨一覧
- よくあるトラブルシューティング（OpenAI エラー時の対処、J-Quants トークン更新方法 等）