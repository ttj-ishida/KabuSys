# KabuSys

バージョン: 0.1.0

日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログなどを含みます。

主な設計方針:
- ルックアヘッドバイアス（未来情報参照）を避ける設計
- DuckDB を中心としたデータ永続化
- J-Quants / OpenAI / kabuステーション 等の外部 API との連携を想定
- 冪等性・フェイルセーフを重視した実装

---

## 機能一覧

- データ ETL
  - J-Quants から株価（OHLCV）・財務・カレンダーを差分取得して DuckDB に保存（pipeline.run_daily_etl 等）
  - 差分取得・バックフィル・品質チェックを含む日次パイプライン
- ニュース収集
  - RSS 取得 → 前処理 → raw_news / news_symbols への保存（news_collector.fetch_rss 等）
  - SSRF / Gzip bomb / トラッキング除去などセキュリティ対策あり
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成した市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ・フォールバック実装
- 研究（Research）
  - ファクター計算（momentum, value, volatility 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等（feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（data.quality）
- 監査ログ
  - strategy → signal → order_request → execution を追跡する監査スキーマ定義と初期化（data.audit.init_audit_db / init_audit_schema）
- 外部クライアント
  - J-Quants API クライアント（data.jquants_client）
  - ETL の保存関数（save_daily_quotes 等）

---

## セットアップ手順（開発/実行環境）

以下は一般的なセットアップ手順の例です。プロジェクト固有の依存は requirements.txt を参照してください。

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 本リポジトリで使用される主な外部パッケージ例:
     - duckdb
     - openai
     - defusedxml
     - など（requirements.txt を参照）

4. 環境変数設定
   - プロジェクトルートの `.env` または `.env.local` に設定するか、OS 環境変数として設定します。
   - 自動読み込み:
     - config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（任意、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）（デフォルト INFO）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な API/ユースケース）

以下は Python REPL またはスクリプトからの簡単な利用例です。すべての関数は duckdb の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

1) DuckDB 接続の作成（デフォルトパス使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを生成（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 環境変数 OPENAI_API_KEY を設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに日次の判定を保存します
```

5) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブルが作成されます
```

6) J-Quants から株価データを個別取得して保存（内部的に使用される例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を利用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
```

注意:
- AI モジュール（news_nlp / regime_detector）は OpenAI の API キーを必要とします（引数経由または環境変数 OPENAI_API_KEY）。
- いくつかの関数は外部 API 呼び出しやネットワークアクセスを伴い、失敗時はフォールバックやログ出力を行いますが、例外ハンドリングを呼び出し側で行ってください。

---

## ディレクトリ構成（主要ファイル）

概要的なツリー（src/kabusys 配下の主要モジュール）:

- src/kabusys/
  - __init__.py  (ライブラリバージョン等)
  - config.py    (環境変数 / 設定管理)
  - ai/
    - __init__.py
    - news_nlp.py         (銘柄別ニュースセンチメント)
    - regime_detector.py  (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント + 保存関数)
    - pipeline.py         (ETL メイン / run_daily_etl 等)
    - etl.py              (ETLResult 再エクスポート)
    - news_collector.py   (RSS 取得・前処理)
    - calendar_management.py (市場カレンダー管理)
    - quality.py          (データ品質チェック)
    - stats.py            (共通統計ユーティリティ)
    - audit.py            (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py  (momentum/value/volatility 等)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - ai/  (上記)
  - research/ (上記)

各モジュールはドキュメント文字列に設計方針・処理フローが詳述されています。実装は基本的に DuckDB 接続を受け取り SQL と純粋 Python で処理します。

---

## 開発時のヒント・注意点

- 自動で .env を読み込む仕組み:
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- DuckDB の executemany に空リストを渡せない制約に配慮した実装が多数あります（空チェックが入っています）。
- OpenAI 呼び出しは JSON mode を利用しており、レスポンスパース失敗時はフォールバック（スコア 0.0 など）するケースがあります。
- ETL / API 呼び出しでは指数的バックオフ・再試行・401 リフレッシュ（J-Quants）等の堅牢性機構が組み込まれています。
- production（本番）で運用する際は KABUSYS_ENV を適切に設定（paper_trading / live）し、ログレベルや監視を整備してください。

---

必要であれば README に追記したい情報（例: requirements.txt の具体的な内容、Docker / systemd サービス定義、運用手順、CI/CD 設定）を教えてください。