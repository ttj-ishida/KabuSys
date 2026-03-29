# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（部分実装）。  
データ取得（J-Quants）、データ品質チェック、ETL、ニュース収集・NLP、リサーチ用ファクター計算、監査ログ（発注追跡）、および市場レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象としたデータプラットフォーム＋リサーチ／取引補助のライブラリ群です。主に以下のレイヤーで構成されています。

- data: J-Quants からのデータ取得クライアント、ETL パイプライン、カレンダー管理、ニュース収集、品質チェック、監査ログ初期化など
- ai: ニュースの NLP スコアリング（OpenAI）と市場レジーム判定
- research: ファクター計算・特徴量解析ユーティリティ
- config: 環境変数／設定管理
- utils: 統計ユーティリティ等

設計上のポイント:
- ルックアヘッドバイアスを避けるため datetime.today() 等を直接参照せず、関数に target_date を明示的に渡す設計
- DuckDB を用いたオンディスク（またはインメモリ）データ管理
- OpenAI（gpt-4o-mini）を利用した JSON モードでの NLP 呼び出し（リトライ・フォールバック実装）
- J-Quants API 呼び出しに対するレートリミットとリトライ処理

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local / OS 環境変数）
- J-Quants API クライアント（株価日足・財務・上場銘柄・市場カレンダー）
  - レート制御、認証トークン自動リフレッシュ、ページネーション対応、冪等保存（ON CONFLICT）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理（URL 正規化・SSRF 対策）
- ニュース NLP（OpenAI）を用いた銘柄別センチメント scoring（score_news）
- 市場レジーム判定（MA200 とマクロニュースの LLM センチメントを合成）（score_regime）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ（zscore_normalize 等）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）と専用 DB 初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの | 記法などを利用）
- DuckDB を利用するためネイティブ環境で問題ないこと

1. リポジトリをクローン／展開
   - 例: git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - openai
     - defusedxml
   - 仮に pip でインストールする場合:
     - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / pyproject.toml がある想定で、それらを使ってください）

4. 環境変数の準備
   - 推奨: プロジェクトルートに `.env` / `.env.local` を置く（自動ロードあり）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   - 自動ロードを無効化する（テスト等）:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースディレクトリを作成（必要に応じて）
   - mkdir -p data

6. （オプション）監査用 DB 初期化
   - Python REPL やスクリプト内で:
     - import duckdb
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")  # または ":memory:"

---

## 簡単な使い方（例）

サンプルコードは Python 内で直接実行・呼び出すことを想定しています。

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を開く
```python
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次）実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（ai.news_nlp）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続、OPENAI_API_KEY を環境変数に設定しておくか api_key 引数で渡す
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- 市場レジーム判定（ai.regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは環境変数 OPENAI_API_KEY を利用
```

- 監査スキーマの初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- リサーチ（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

momentums = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
values = calc_value(conn, date(2026,3,20))
```

- 統計ユーティリティ
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(momentums, ["mom_1m", "mom_3m"])
```

注意点:
- score_news / score_regime は OpenAI API を呼び出すため API キーが必須です。未設定時は ValueError が発生します。
- ETL / J-Quants クライアントは API レート制限や認証に依存します。設定されたトークンとネットワーク環境を確認してください。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なモジュール一覧（提供コードに基づく）:

- src/kabusys/
  - __init__.py
  - config.py           # 環境変数・設定ロード
  - ai/
    - __init__.py
    - news_nlp.py       # ニュース NLP スコアリング
    - regime_detector.py# 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETL 公開インターフェース（ETLResult）
    - news_collector.py    # RSS ニュース取得・前処理
    - calendar_management.py # マーケットカレンダー管理
    - quality.py           # データ品質チェック
    - stats.py             # 統計ユーティリティ（zscore_normalize）
    - audit.py             # 監査ログ（スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py   # モメンタム / ボラ / バリュー計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリー
  - monitoring/ (README に含まれる可能性あり / 実装は別)
  - strategy/ (戦略・発注ロジックは別モジュールで実装想定)
  - execution/ (ブローカー接続・発注ロジックは別モジュールで実装想定)

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 機能を利用する場合）

任意／デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env の書式:
- KEY=VALUE（コメント行は # で始める）
- export KEY=VALUE の形式もサポート
- 値は引用符 ' or " で囲むことが可能（内部でエスケープ処理）

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定
  - settings モジュールのプロパティは必須変数をチェックします。.env を用意するか環境変数を設定してください。

- OpenAI / J-Quants API の認証エラー
  - トークンが古い、または権限不足の可能性。J-Quants は refresh token → id token を取得するフローを使用します。

- DuckDB 関連のエラー
  - テーブル未作成のケースがあるため、ETL 実行前に適切なスキーマ初期化が必要な場合があります。監査スキーマは init_audit_schema で作成可能。

- ニュース収集で XML パースエラーやサイズ超過
  - RSS ソースが不正、またはレスポンスが大きすぎる場合はスキップされます。news_collector のログを確認してください。

---

## ロギング

- settings.log_level でログレベルを設定できます（環境変数 LOG_LEVEL）。
- 各モジュールは標準の logging を用いて情報・警告・エラーを出力します。運用環境では適切なハンドラ（ファイル/Stdout）を設定してください。

---

## 今後の拡張 / 注意点

- strategy / execution 層（実際の売買ロジック・ブローカー連携）は本コードベースでは分離されています。実運用での約定処理は十分なテストと冗長性設計が必要です。
- LLM 呼び出しはコストが発生します。バッチサイズや呼び出し頻度は運用ポリシーに合わせて調整してください。
- J-Quants のレート制限を守るため、fetch 周りは内部でスロットリング／リトライを実装していますが、大量リクエスト時は注意してください。

---

必要であれば、README に含めるサンプル .env.example や、各モジュールの詳細な API 使用例（関数別）を追記できます。続きを希望すれば教えてください。