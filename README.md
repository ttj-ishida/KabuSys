# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリ。J-Quants からのデータ取得（株価・財務・マーケットカレンダー）やニュース収集、LLM を用いたニュースセンチメント評価、市場レジーム判定、ETL パイプライン、データ品質チェック、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API を用いた株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - ETL の結果を表現する ETLResult クラス
- データ品質管理
  - 欠損データ、スパイク検出、重複、日付不整合などのチェック（quality モジュール）
- ニュース収集 / NLP
  - RSS からのニュース収集（SSRF 対策・前処理・記事IDの正規化）
  - OpenAI（gpt-4o-mini）を用いたニュースごとの銘柄センチメントスコアリング（news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を算出（regime_detector.score_regime）
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）やファクター統計サマリ
- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定をトレースする監査テーブル群（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数 / .env(.local) 自動読み込み、必須値チェック（config.settings）

---

## 必須環境変数（代表例）

このプロジェクトはいくつかの外部サービス／機能に依存します。最低限設定が必要な環境変数（.env に設定する想定）:

- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（ETL／jquants_client.get_id_token に使用）
- OPENAI_API_KEY：OpenAI API キー（news_nlp / regime_detector の LLM 呼び出しに使用）
- KABU_API_PASSWORD：kabuステーション API のパスワード（発注連携等）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（監視通知等）
- SLACK_CHANNEL_ID：Slack チャネル ID（通知送信先）

オプション・デフォルト（環境変数が未設定の場合のデフォルト値）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: INFO（または DEBUG / WARNING / ERROR / CRITICAL）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH: data/execution.pid
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` を自動で読み込みます。`.env.local` は上書き優先で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 依存パッケージ（代表）

- duckdb
- openai
- defusedxml
- （標準ライブラリのみで実装されている箇所も多いですが、上記は必須または推奨）

インストール方法はプロジェクト構成によりますが、開発環境であれば通常は次のようにします：

例:
- pip install -e .  (プロジェクトがpyproject/セットアップ済みの場合)
- または pip install duckdb openai defusedxml

requirements.txt / pyproject.toml がある場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存関係をインストール
   - pip install -r requirements.txt
   - または pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成し、必要なキーを設定（下に例を示します）
5. DuckDB データベース準備
   - デフォルトでは settings.duckdb_path が `data/kabusys.duckdb`。親ディレクトリがない場合は自動作成されるように呼び出し側で配慮してください。
6. （オプション）監査 DB の初期化
   - init_audit_db を使って監査専用 DB を初期化できます（例を後述）

例 .env（最小）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API と実行例）

下記はライブラリを直接 Python から利用するための簡単な例です。DuckDB 接続には duckdb.connect を使います。

- 共通: DuckDB 接続例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパス
```

- 日次 ETL を実行（prices / financials / calendar の差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb.DuckDBPyConnection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア生成（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```
- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# テーブルが作成された接続オブジェクトが返る
```

- J-Quants の ID トークン取得（低レベル）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

- RSS フィード取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意:
- OpenAI 呼び出しは gpt-4o-mini を想定（JSON mode）で実装されています。API キーが必要です。
- J-Quants API にはレート制限（120 req/min）があり、jquants_client 内で制御しています。
- API 呼び出しはネットワーク障害やレート制限に対してリトライやフェイルセーフを実装していますが、キーやトークンが未設定だと例外が発生します。

---

## 推奨実行フロー（日次バッチの例）

1. ETL（run_daily_etl）を走らせてデータを最新化
2. news_nlp.score_news でニュースセンチメントを ai_scores に書き込む
3. research モジュールや strategy 層でファクターを計算・検証
4. regime_detector.score_regime で当日の市場レジームを判定して market_regime テーブルへ保存
5. 監査ログ（signal / order_requests / executions）は発注フロー実行時に保持

---

## ディレクトリ構成（主要ファイルの説明）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージのトップ。__version__ を定義。

- config.py
  - 環境変数と .env 自動ロード、Settings クラス（settings オブジェクト）を提供。

- ai/
  - __init__.py
  - news_nlp.py：ニュースセンチメント解析と ai_scores への書き込み（OpenAI 経由）
  - regime_detector.py：ETF 1321 の MA 乖離とマクロニュースを合成して市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py：J-Quants API クライアント（取得・保存ロジック・レートリミッタ）
  - pipeline.py：ETL パイプライン（run_daily_etl 等）
  - etl.py：ETLResult の再エクスポート
  - news_collector.py：RSS 取得・前処理・raw_news への保存ユーティリティ
  - calendar_management.py：市場カレンダー管理・営業日判定ユーティリティ
  - stats.py：z-score 正規化などの統計ユーティリティ
  - quality.py：データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py：監査ログ用テーブル定義・初期化（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py：Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py：将来リターン、IC、ファクター統計、rank

その他:
- 各モジュールは DuckDB 接続を受け取る設計で、外部 API への直接的な発注等は含まれていません（研究・データ基盤部分に集中）。

---

## 設計上の注意点 / 重要な挙動

- ルックアヘッドバイアス対策
  - 多くの関数は date.today() や datetime.now() を内部で直接参照せず、呼び出し元が target_date を指定することでバックテストでのルックアヘッドを防止しています。
- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE（または INSERT ... ON CONFLICT）で冪等的に保存します。
- フェイルセーフ
  - LLM 呼び出しや外部 API が失敗した場合、多くの箇所で安全側の値（例: macro_sentiment=0.0）にフォールバックし、処理を継続する設計です。
- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査・プライベート IP ブロック）や defusedxml を利用した XML の安全パースを実装しています。

---

## 貢献 / テスト

- モジュールはユニットテストで差し替え可能な設計（例: _call_openai_api を patch してテスト）になっています。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑止するとテストが安定します。

---

以上です。追加で README に含めたい実行スクリプト例（cron ジョブや systemd ユニット、Dockerfile、CI 設定例）や .env.example の具体的なテンプレートが必要でしたら知らせてください。