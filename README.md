# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ (KabuSys)。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを提供します。

---

## 主要機能
- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - ETL の差分・バックフィル処理（DuckDB 保存、冪等性）
  - データ品質チェック（欠損／スパイク／重複／日付不整合）
- ニュース収集 / NLP
  - RSS フィード収集と前処理（SSRF対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた記事群の銘柄別センチメントスコア化（ai_scores テーブルへ保存）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' 判定
- リサーチ / ファクター作成
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査スキーマ初期化ユーティリティ（DuckDB）
- 設定管理
  - .env / 環境変数読み込み（自動ロード、優先順位: OS env > .env.local > .env）
  - 必須設定は Settings 経由で取得（JQUANTS_REFRESH_TOKEN 等）

---

## 必要要件（例）
- Python 3.9+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外のパッケージはプロジェクトで明示してください）

例（pip）:
pip install duckdb openai defusedxml

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## 環境変数 / .env
設定は環境変数、もしくはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（CWD に依存せずパッケージルートを探索）。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しで使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 `.env`:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

設定はコードから次のように参照できます:
from kabusys.config import settings
token = settings.jquants_refresh_token

---

## セットアップ手順（開発環境向け）
1. リポジトリをチェックアウト
2. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate
3. 必要なパッケージをインストール
   pip install duckdb openai defusedxml
   （プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを使用）
4. プロジェクトルートに `.env` を配置し、上記の必須設定を記載
5. DuckDB ファイル保存先ディレクトリ（例: data/）を作成:
   mkdir -p data

---

## 使い方（簡単な例）
以下は典型的な利用フローのサンプルです。実行は Python スクリプトや REPL で行います。

1) DuckDB 接続の作成:
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL の実行:
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュース NLP スコアリング（ai_scores への書き込み）:
from kabusys.ai.news_nlp import score_news
from datetime import date
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")

4) 市場レジーム判定:
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

5) 監査ログ DB の初期化:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" 可

6) リサーチ用ファクター計算:
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数を受け取ります。省略した場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / データ取得は J-Quants の認証が必要です。JQUANTS_REFRESH_TOKEN を設定してください。
- モジュールは Look-ahead バイアス防止の観点から内部で date.today() を不用意に参照しない設計になっていますが、target_date の指定や ETL の実行タイミングには注意してください。

---

## 主要モジュール / ディレクトリ構成
（src/kabusys 配下の主要ファイル・サブパッケージ）

- kabusys/
  - __init__.py
  - config.py                : 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            : ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py     : マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得・保存関数）
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - etl.py                 : ETLResult の再エクスポート
    - news_collector.py      : RSS 収集・前処理（SSRF対策等）
    - calendar_management.py : 市場カレンダー管理（営業日判定・更新ジョブ）
    - quality.py             : データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py               : 統計ユーティリティ（zscore 正規化等）
    - audit.py               : 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     : Momentum/Value/Volatility の計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー 等

---

## ログ・実行環境
- ログレベルは環境変数 `LOG_LEVEL` で制御（デフォルト INFO）。
- 実行モードは `KABUSYS_ENV` で選択可能（development / paper_trading / live）。
- 自動で .env を読み込む際の優先順位: OS 環境 > .env.local > .env。テスト等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## テスト / モックについて
- OpenAI 呼び出しやネットワーク部分はユニットテストでモック差し替えが想定されています（例: news_nlp._call_openai_api, regime_detector._call_openai_api, news_collector._urlopen など）。
- DuckDB 接続をメモリ（":memory:"）で作成して単体テストを行えます。

---

## 注意事項 / ベストプラクティス
- production（ライブ）環境では `KABUSYS_ENV=live` を設定し、ログや通知の取り扱いに注意してください。
- OpenAI の呼び出しはコスト・レイテンシが発生します。バッチサイズやリトライ方針はモジュール内の定数で制御されていますが、運用時に調整が必要です。
- J-Quants API のレート制限に合わせて RateLimiter が組み込まれています。大量の並列呼び出しは避ける設計にしてください。
- 監査ログ（audit）スキーマは削除しない前提の設計です。既存レコードの保全に注意してください。

---

もし README にさらに追加したい具体的な実行例（CLI スクリプトの例、docker-compose、CI 設定、依存一覧など）があれば教えてください。README をそれに合わせて拡張します。