# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（取引フローのトレーサビリティ）など、トレーディングシステムの基盤機能を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() / datetime.today() を安易に参照しない）
- DuckDB を中心としたローカルデータストアと SQL ベース処理
- 外部 API 呼び出し（J-Quants / OpenAI 等）は堅牢なリトライ・レート制御を実装
- 冪等保存と監査ログによるトレーサビリティ確保

---

## 機能一覧
- 環境設定管理（.env の自動読み込み、必須キー検証）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 上場銘柄一覧取得
- ETL パイプライン（差分取得、保存、品質チェック）
  - run_daily_etl 等の高レベル API を提供
- ニュース収集（RSS）と前処理：SSRF 対策・トラッキングパラメータ除去・サイズ上限
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコアリング）
  - score_news(conn, target_date, api_key=None)
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
  - score_regime(conn, target_date, api_key=None)
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 監査ログ（signal_events / order_requests / executions の作成・初期化）
- リサーチ用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化 等）
- マーケットカレンダー管理（営業日判定・前後営業日の取得等）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上を推奨（型表記や挙動に依存）
- DuckDB、OpenAI SDK、defusedxml などが必要

例: 仮想環境を作って依存を入れる
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 追加で必要なパッケージがあればここに追記してください
```

パッケージをローカル開発モードでインストールする場合:
```bash
pip install -e .
```
（プロジェクトに pyproject.toml / setup.cfg がある場合）

必須環境変数（少なくとも以下を設定してください）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN       : Slack 通知用トークン（通知統合を使う場合）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector を使う場合）

オプション（デフォルト値あり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL   : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite 用の監視 DB（デフォルト: data/monitoring.db）

.env の自動読み込み
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を自動的に読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

---

## 使い方（主な例）

1) DuckDB 接続の作成（デフォルトファイルを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（J-Quants からデータ取得、品質チェック含む）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュースの NLP スコア生成（OpenAI API を使用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

4) 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_kabusys.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

6) リサーチ用途（ファクター計算や統計）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# Zスコア正規化例
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

7) マーケットカレンダー操作
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day

d = date(2026, 3, 20)
is_trading = is_trading_day(conn, d)
next_td = next_trading_day(conn, d)
prev_td = prev_trading_day(conn, d)
```

注意点
- OpenAI・J-Quants 呼び出しはネットワークやレート制限の影響を受けます。呼び出しは例外を返す場合がありますので適切にハンドリングしてください。
- score_news / score_regime は API キーを引数で渡すか、環境変数 OPENAI_API_KEY を参照します。

---

## 環境変数（主な一覧）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu API) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須 for Slack) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live')
- LOG_LEVEL — ログレベル（'DEBUG' 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（任意）

---

## ディレクトリ構成（主なファイル）
src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント・保存処理
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETL インターフェース再エクスポート
  - news_collector.py       — RSS ニュース収集・前処理
  - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — 将来リターン・IC・統計サマリー等
- research/... (上記参照)

その他
- data/ (デフォルトのデータ保存ディレクトリ、DuckDB ファイル等)

---

## ログ / デバッグ
- LOG_LEVEL 環境変数でログレベルを変更できます（INFO デフォルト）。
- 各モジュールは logging.getLogger(__name__) を利用しており、ルートロガーの設定に従います。

---

## テスト・モック
- OpenAI やネットワーク呼び出しはテスト時にモック可能な設計です（モジュール内の _call_openai_api や HTTP 関数をパッチする等）。
- .env 自動読込はテスト環境で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ライセンス / 貢献
- この README はコードベースから生成したものであり、実際のリポジトリには別途 LICENSE や CONTRIBUTING ガイドがある可能性があります。プロジェクトに貢献する場合はそれらを参照してください。

---

README の内容修正や特定機能の利用例（例えば発注フロー・Slack 通知・kabu API と連携した実行例など）を追加したい場合は、どの機能の例が欲しいか教えてください。必要に応じて具体的なサンプルコードを追記します。