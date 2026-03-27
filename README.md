# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI 等を組み合わせ、データ収集（ETL）・品質チェック・ニュース NLP・市場レジーム判定・研究用ファクター計算・監査ログ管理などの機能を提供します。

主な用途:
- J-Quants からの株価・財務・カレンダー等の差分 ETL
- RSS ニュース収集と銘柄ごとの NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究向けファクター計算 / 将来リターン / IC 計測
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ初期化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（Settings クラス）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェックの統合
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - fetch_* / save_* 関数（raw_prices, raw_financials, market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存設計
- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合などを検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日の取得、カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマと初期化ユーティリティ
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を使った銘柄別ニュースセンチメントのバッチ評価（JSON mode）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の MA 乖離とマクロニュース LLM スコアを組合せた日次レジーム判定
- 研究ユーティリティ（kabusys.research）
  - momentum / volatility / value 等のファクター計算、forward returns、IC、統計サマリ
- 汎用統計ユーティリティ（kabusys.data.stats）
  - z-score 正規化等

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型注釈に union 型などを使用）
- DuckDB が利用されます（pip パッケージ duckdb）
- OpenAI API を利用する場合は openai パッケージが必要
- RSS 解析で defusedxml を使用

推奨インストール（仮想環境内で実行）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて他パッケージを追加
```

環境変数 / .env:
プロジェクトは起点ファイルからプロジェクトルート（.git または pyproject.toml）を探索し、そのルートにある `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる主要な環境変数（機能によって必要なものが異なります）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（発注系）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID : Slack チャネル ID
- OPENAI_API_KEY : OpenAI を利用する場合（news_nlp / regime_detector）
オプション:
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）

例: `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な例）

以下は Python REPL / スクリプトでの利用例です。各例で DuckDB 接続オブジェクト（duckdb.connect）を渡します。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの AI スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数で設定されている想定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

3) 市場レジームをスコアする（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

5) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

6) カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- AI 関連関数は OpenAI API を呼び出します。API キーおよびリクエスト制約（料金・レート）に注意してください。
- run_daily_etl 等は内部で ETL の各ステップを個別に例外処理します。戻り値の ETLResult で各ステップの成否や品質問題を確認してください。

---

## 設定・運用のポイント

- 環境変数は .env / .env.local で管理できます。プロジェクトルートに配置すると自動読み込みされます。
- テストや CI で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはリトライやフォールバック（失敗時は中立スコア）を実装していますが、API の可用性や課金には注意してください。
- DuckDB の executemany は空リストを渡すとエラーになるバージョンがあるため（コード内で考慮済み）ETL 実行時に空パラメータは送られません。
- 監査ログは削除しない前提で設計されています。order_request_id を冪等キーとして利用することで二重発注を防止します。

---

## ディレクトリ構成（抜粋）

プロジェクトは主に src/kabusys 以下に実装が配置されています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - pipeline.py              — ETL パイプライン / run_daily_etl 等
    - etl.py                   — ETLResult 再エクスポート
    - news_collector.py        — RSS 収集 / raw_news への保存
    - calendar_management.py   — 市場カレンダー管理（営業日判定 など）
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore）
    - audit.py                 — 監査ログスキーマの初期化
  - research/
    - __init__.py
    - factor_research.py       — momentum / value / volatility
    - feature_exploration.py   — forward returns / IC / rank / summary
  - monitoring/ (※監視系モジュールがここに入る想定)
  - strategy/ (戦略・シグナル実装用モジュール想定)
  - execution/ (発注・約定処理用モジュール想定)

（上記はコードベースに含まれる主要モジュールの一覧です。実運用ではさらに CLI / scheduler / worker などを併設して運用します）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていないか確認してください。プロジェクトルートが .git / pyproject.toml によって検出されない場合、自動読み込みはスキップされます。
- OpenAI レスポンスのパース失敗
  - library は JSON mode を利用し厳格な JSON を期待していますが、API 側の出力差異に対応するためフォールバック処理があります。API エラー時はフェイルセーフとして中立スコア（0.0）にフォールバックします。
- DuckDB に INSERT できない / executemany の挙動
  - コード内で空リストを渡すケースをチェックして回避していますが、DuckDB のバージョン差に起因する問題があれば DuckDB のバージョンを確認してください。

---

この README はソースコードの概要に基づく簡易ドキュメントです。各モジュール内の docstring（ソース内コメント）に詳細な設計意図・使い方・例が記載されていますので、実装の確認や拡張の際は該当ファイルを参照してください。