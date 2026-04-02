# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム向けライブラリ群です。  
データ ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログなど、量的運用に必要な主要機能を提供します。

---

## 概要

主な目的は以下です。

- J-Quants API からの差分取得・ETL（株価・財務・市場カレンダー）
- ニュース収集・NLP による銘柄別センチメントスコア生成（OpenAI を使用）
- マーケットレジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティなど）
- データ品質チェック、監査ログ（order/signal/execution のトレーサビリティ）
- DuckDB を中心とした局所 DB 運用を想定

このリポジトリはライブラリ形式で、他プロセスやジョブからインポートして利用します。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / token リフレッシュ、レート制御、リトライ）
  - ニュース収集（RSS の正規化、SSRF 防止、前処理）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（z-score 正規化）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でセンチメントを算出し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・管理（.env 自動読み込み、settings オブジェクト）

---

## 必要条件・依存

- Python 3.10+
- 主な Python パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml

（requirements.txt は本リポジトリに含まれていない想定なので、上記パッケージをインストールしてください。）

例:
```
python -m pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

config.Settings から参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーションの API パスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : sqlite 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH         : 実行 PID 保存先（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV           : 実行環境 (development|paper_trading|live)
- LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY        : OpenAI API キー（ai モジュールで利用）

自動的に .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数優先）。  
自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成します
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   ```

3. 環境変数を準備
   - プロジェクトルートに `.env` を作成する（.env.example を参照）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - OpenAI を使う機能を使う場合は OPENAI_API_KEY を設定

4. （任意）パッケージを開発モードでインストール
   ```
   python -m pip install -e .
   ```

---

## 使い方（簡単な例）

以下はライブラリ API の代表的な使い方例です。DuckDB 接続は settings.duckdb_path を使うことを想定しています。

- ETL（日次パイプライン）の実行
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI に依存）
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key=None -> OPENAI_API_KEY を参照
print("written:", n_written)
```

- 市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログスキーマの初期化（監査用 DB を作る）
```
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)
# conn をそのまま使用して監査テーブルに書き込み可能
```

- 研究用ファクター計算の利用例
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI の API を用います。OPENAI_API_KEY を設定してください。
- すべての関数は「ルックアヘッドバイアス」を避けるため、内部で date.today() を勝手に参照しない方針です。target_date を明示して呼び出してください。

---

## よく使うモジュール一覧（簡易説明）

- kabusys.config
  - settings: 環境変数ラッパー（必須値のチェック、パスの Path 返却等）
  - .env 自動読み込み（プロジェクトルートにある .env / .env.local）

- kabusys.data
  - pipeline: ETL のエントリポイント run_daily_etl 等。ETLResult クラスを返す
  - jquants_client: J-Quants API との通信・保存ロジック
  - news_collector: RSS 取得 → raw_news への保存ロジック
  - calendar_management: 営業日判定・カレンダー更新 job
  - quality: データ品質チェック
  - stats: zscore_normalize などの統計関数
  - audit: 監査ログ（テーブル作成・初期化）

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: マーケットレジームを market_regime に保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（提供済みファイルに基づくスナップショット）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - audit.py
      - etl.py
      - pipeline.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - factor_research.py
      - feature_exploration.py

（上は抜粋です。実際のリポジトリではさらにモジュールがある場合があります。）

---

## 運用上の注意

- 環境変数の管理: .env / .env.local を用いて秘密情報をローカルで管理してください。CI/CD 等でシークレットを注入する場合は OS 環境変数を優先してください。
- OpenAI 呼び出しは課金が発生します。API キーの権限と使用量に注意してください。
- J-Quants API はレート制限があります（モジュール内でレート制御あり）。大量一括実行時は注意してください。
- DuckDB バージョン依存や executemany の制約に注意（pipeline 内に互換性考慮の実装あり）。
- テスト用に自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## サポート / 貢献

バグ報告や機能提案は Issue を立ててください。プルリクエストは歓迎します。コードスタイルやユニットテストを含めた変更をお願いします。

---

以上。必要であれば README に「実行例スクリプト」「.env.example のテンプレート」「よくあるトラブルシューティング」を追記します。どの項目を詳細化したいか教えてください。