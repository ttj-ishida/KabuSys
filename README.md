# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）。  
データ収集・ETL、データ品質チェック、ニュースNLP（OpenAI 経由）を用いた銘柄ごとのセンチメント付与、マーケットレジーム判定、研究用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得 / ETL（J-Quants API 経由）
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得と DuckDB へ冪等保存
  - 差分取得・バックフィル・ページネーション・レートリミット・リトライ対応
- ニュース収集
  - RSS フィードの安全な取得（SSRF/サイズ/GZIP 対策）、記事の正規化、raw_news への保存
- ニュースNLP / AI
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースを銘柄単位にセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロ記事センチメントを合成して市場レジーム（bull/neutral/bear）判定
  - API 呼び出しは再試行・バックオフ・フェイルセーフを備える
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出し QualityIssue を返す
- マーケットカレンダー管理
  - market_calendar テーブルによる営業日判定、next/prev_trading_day、期間内営業日列挙、JPX カレンダー更新ジョブ
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル DDL と初期化ユーティリティ（DuckDB）
  - order_request_id による冪等性を想定した設計

---

## 要件（主要なライブラリ）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外は上記のインストールを想定）

例:
```
pip install duckdb openai defusedxml
```

プロジェクトをパッケージとして利用する場合は setup / pyproject を参照して pip install -e . を検討してください。

---

## セットアップ

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にしたい場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（代表例 — .env に設定する）:
- JQUANTS_REFRESH_TOKEN=...        # J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD=...            # kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN=...              # Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID=...             # Slack 通知チャンネルID（必須）

任意（デフォルトあり）:
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1            (自動 .env 読込を抑止)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)

.env ファイルのパーサはシェルスタイルの export プレフィックスやクォート、行末コメント等に対応しています。

---

## 使い方（簡単なコード例）

※ すべての関数は DuckDB 接続（duckdb.connect(...) の接続オブジェクト）を受け取る形が多いです。

1) DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

3) ニューススコアを計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されているか、api_key 引数を渡す
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("written:", n_written)
```

4) 市場レジームをスコアリングする
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

5) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査スキーマを作成済みの DuckDB 接続
```

6) 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

ログの出力レベルは環境変数 `LOG_LEVEL` で制御できます。

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - モジュールは内部で datetime.today()/date.today() を不用意に参照せず、target_date を明示的に与えて動作するよう設計されています（研究・バックテストでの安全性重視）。
- 冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE 等の手法で冪等に保存されます。
- API 呼び出し:
  - J-Quants / OpenAI 呼び出しにはレート制御・リトライ・バックオフが組み込まれています。OpenAI キーは環境変数 OPENAI_API_KEY、または関数の api_key 引数で渡せます。
- 自動 .env 読み込み:
  - プロジェクトルートを .git または pyproject.toml で探索して `.env` / `.env.local` を読み込みます。自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/__init__.py
  - パッケージ定義（version, subpackages）
- src/kabusys/config.py
  - 環境変数 / .env ロード、設定管理（Settings オブジェクト）
- src/kabusys/ai/
  - news_nlp.py              : ニュースを銘柄別に集約して OpenAI でセンチメント付与（score_news）
  - regime_detector.py      : ETF MA とマクロ記事を組み合わせた市場レジーム判定（score_regime）
- src/kabusys/data/
  - pipeline.py             : ETL パイプライン（run_daily_etl 等）、ETLResult
  - jquants_client.py       : J-Quants API クライアント（fetch_*/save_*）
  - news_collector.py       : RSS 収集、安全対策・正規化・raw_news への保存
  - calendar_management.py  : 市場カレンダー管理、営業日判定、calendar_update_job
  - quality.py              : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py                : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                : 監査ログ（DDL / 初期化関数 / init_audit_db）
  - etl.py                  : ETLResult の再エクスポート
- src/kabusys/research/
  - factor_research.py      : ファクター（モメンタム / ボラティリティ / バリュー）計算
  - feature_exploration.py  : 将来リターン、IC、統計サマリー、ランク関数
  - __init__.py             : 研究用 API のエクスポート
- src/kabusys/ai/__init__.py  : AI モジュールの公開インターフェース
- src/kabusys/research/__init__.py

（上記はコードベースの主要モジュールまとめです。詳細は各ソースファイルの docstring を参照してください。）

---

## よくある操作 / トラブルシュート

- OpenAI 呼び出しで失敗が発生する場合:
  - OPENAI_API_KEY の有無を確認。関数呼び出しの api_key 引数で上書き可能。
  - API レスポンスのパース失敗などはログに WARNING を出しフェイルセーフ（スコア=0 等）で継続する実装箇所があります。
- J-Quants API 認証エラー:
  - JQUANTS_REFRESH_TOKEN を .env に設定しているか確認。jquants_client.get_id_token() は自動でリフレッシュを試みます。
- .env 自動読み込みが期待どおり動作しない場合:
  - プロジェクトルート検出は __file__ の親階層から `.git` または `pyproject.toml` を探索します。別の場所で実行している場合は明示的に環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を使い手動でロードしてください。

---

## 参考・ライセンス

この README はコードの docstring と実装に基づいています。実際の運用では API キーや本番環境設定に充分注意し、安全にテスト（paper_trading 等）してから live を利用してください。

必要であれば README の英語版や、各モジュール別の詳細ドキュメント（関数シグネチャ、戻り値、例外仕様）を追加で作成します。