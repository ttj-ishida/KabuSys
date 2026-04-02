# KabuSys

KabuSys は日本株のデータ収集・品質管理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログを含む自動売買 / 研究用の基盤ライブラリです。DuckDB を用いたローカルデータプラットフォームと外部 API（J-Quants、OpenAI など）を組み合わせて、ETL / 解析 / モニタリング / 発注トレースの基本機能を提供します。

---

## 主な特徴

- データ ETL
  - J-Quants API から株価（日足）・財務データ・JPX カレンダーを差分取得・保存
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
  - ETL 実行結果を ETLResult で集約

- データ品質チェック
  - 欠損、主キー重複、将来日付、前日比スパイクなどのチェック
  - QualityIssue オブジェクトで検出内容を集約

- ニュース収集 / ニュース NLP
  - RSS フィードから記事を収集して raw_news に保存（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア生成（ai_scores）
  - JSON Mode を使った堅牢なレスポンス検証とリトライ

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジームを判定（bull / neutral / bear）
  - OpenAI 呼び出しはリトライ・フォールバック実装あり

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマ初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ管理

- リサーチ用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー

---

## 必要条件

- Python 3.10 以上（型注釈 Path | None 等を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトで使用する実環境により追加パッケージが必要になる場合があります）

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローンして移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。ローカル開発用に pip install -e . などを行ってパッケージとしてインストールできます。

4. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として必要な設定を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須の環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN: Slack 通知（該当機能使用時）
- SLACK_CHANNEL_ID: Slack チャネル ID

その他（デフォルトあり）

- KABU_API_PASSWORD, KABU_API_BASE_URL
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

例 .env（抜粋）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な API）

以下は Python スクリプト／REPL から直接呼び出す例です。DuckDB コネクション（duckdb.connect）を渡して利用します。

1) DuckDB 接続を作成する
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（calendar / prices / financials を差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントのスコアリング（ai_scores に書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

4) 市場レジーム判定（market_regime に書き込む）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査専用 DB を用意）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
```

6) ファクター計算 / リサーチ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

---

## 主なモジュール / API 一覧

- kabusys.config
  - settings: 環境変数経由で各種設定にアクセス

- kabusys.data
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: J-Quants API の取得・保存ユーティリティ（fetch_* / save_*）
  - news_collector.fetch_rss, preprocess_text（RSS 収集）
  - quality.run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - audit.init_audit_db / init_audit_schema

- kabusys.ai
  - news_nlp.score_news（記事を銘柄別にスコアリングして ai_scores に保存）
  - regime_detector.score_regime（マクロセンチメント＋ETF MA 乖離で日次レジーム判定）

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

---

## ディレクトリ構成

（ソースツリーの抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数ロードと Settings
    - ai/
      - __init__.py
      - news_nlp.py                  # ニュースセンチメント (OpenAI)
      - regime_detector.py           # 市場レジーム判定
    - data/
      - __init__.py
      - pipeline.py                  # ETL パイプライン
      - jquants_client.py            # J-Quants API クライアント + 保存処理
      - news_collector.py            # RSS 収集、安全対策あり
      - quality.py                   # データ品質チェック
      - calendar_management.py       # マーケットカレンダー管理
      - audit.py                     # 監査ログスキーマ初期化
      - stats.py                     # 共通統計ユーティリティ
      - etl.py                       # ETLResult エクスポート
    - research/
      - __init__.py
      - factor_research.py           # ファクター計算
      - feature_exploration.py       # 将来リターン・IC・統計サマリー

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアスの防止:
  - モジュール内の多くの関数は date / target_date を明示的に受け取り、datetime.today() を内部で参照しない設計です。バックテストでの正確性を意識しています。

- OpenAI 呼び出し:
  - gpt-4o-mini を想定し、JSON Mode を利用して厳密な JSON 出力を期待します。API エラー時はフォールバック（スコア 0.0）やリトライを行う実装です。

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml の検出）にある `.env` / `.env.local` を自動で読み込みます。テスト等で自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB 互換性:
  - 一部の処理（executemany 空リスト回避、リスト型バインドの扱いなど）は DuckDB のバージョン差を考慮しています。DuckDB のバージョンに依存する挙動があるため、動作確認済みバージョンの利用を推奨します。

---

## さらに進めるには

- 本 README に記載した環境変数を設定して ETL を実行し、データが格納されることを確認してください。
- OpenAI を利用する機能（news_nlp, regime_detector）は API 利用料が発生します。デバッグ時はモック化してテストすることを推奨します。
- 監査ログスキーマを初期化して、signal → order_request → execution のフローを検証してください。

---

もし README に追記したい項目（例: CI / テスト実行方法、開発用の docker-compose 設定、requirements.txt の候補、各種 SQL スキーマ定義の詳細など）があれば教えてください。必要に応じてサンプル .env.example や簡易デプロイ手順も作成します。