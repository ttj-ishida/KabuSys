# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI（LLM）など外部データを取り込み、ETL・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログなどのユーティリティを提供します。

主に研究（Research）・データ基盤（Data）・AI（ニュースNLP / レジーム判定）・監視/実行の各層で構成され、バックテストや実運用で使えるよう設計されています。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・上場情報・JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / upsert）
  - 差分更新・バックフィルロジック

- データ品質管理
  - 欠損・重複・スパイク・日付不整合などのチェックを集約して実行する `data.quality.run_all_checks`

- ニュース収集・NLP
  - RSS 取得・前処理（URL 正規化・トラッキング除去・SSRF 対策）
  - OpenAI（gpt-4o-mini 等）を使った銘柄別センチメント算出（`ai.news_nlp.score_news`）
  - レスポンス検証・バッチ処理・リトライ・スコアクリップ

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（`ai.regime_detector.score_regime`）
  - ルックアヘッドバイアス回避の設計

- リサーチユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（`research.factor_research`）
  - 将来リターン計算、IC（Spearman）や統計サマリー（`research.feature_exploration`）
  - Zスコア正規化ユーティリティ（`data.stats.zscore_normalize`）

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution を追跡する監査テーブルの初期化・ユーティリティ（`data.audit.init_audit_db` / `init_audit_schema`）
  - 発注冪等キー（order_request_id）等の設計を含むスキーマ

- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）と必須環境変数取得ラッパー（`config.settings`）

---

## 前提（Prerequisites）

- Python 3.10+
  - 本ライブラリは型ヒントで PEP 604 の `X | Y` を使っているため Python 3.10 以上を推奨します
- 主要依存ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml

pip でインストールする場合の例:
```bash
pip install duckdb openai defusedxml
# またはプロジェクト配布に requirements.txt がある場合:
# pip install -r requirements.txt
```

開発環境ではパッケージを editable インストールすることが便利です:
```bash
pip install -e .
```

---

## 環境変数（主なもの）

このパッケージは .env / .env.local / OS 環境変数から設定を読み込みます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。必須の環境変数は不足時に ValueError が発生します。

主な変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu ステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しで使用（news_nlp / regime_detector 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/...）

例 (.env):
```env
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成（任意）
```bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
# .venv\Scripts\activate    # Windows
```

3. 依存インストール
```bash
pip install -e .            # もし setup.py/pyproject がある場合
# または最低限:
pip install duckdb openai defusedxml
```

4. 環境変数設定
- プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
- `.env.local` を開発用に上書きで用いることができます（`.env.local` は自動的に `.env` より優先して読み込まれます）。

5. データベース用ディレクトリ作成（必要なら）
```bash
mkdir -p data
```

---

## 使い方（主要な API / 例）

以下はライブラリの代表的な使い方例です。すべて DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- 設定オブジェクト / 環境変数参照
```python
from kabusys.config import settings
print(settings.duckdb_path)          # Path オブジェクト
print(settings.jquants_refresh_token)  # 必須トークン（未設定なら ValueError）
```

- ETL（日次 ETL を実行）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
print(result.to_dict())
```

- ニュース NLP スコア算出（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- リサーチ: ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

- 監査ログ DB 初期化（監査用の DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

---

## 実装上の注意点（設計方針の要約）

- ルックアヘッドバイアス回避
  - 多くの処理で datetime.today()/date.today() を内部参照せず、必ず caller が target_date を明示できるように設計されています。
  - DB クエリは target_date より前のデータのみ参照するなどの配慮があります。

- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants 等）での失敗は多くの場面で例外を投げるのではなく、ログ出力してデフォルト値（例: 0.0）にフォールバックする処理が組み込まれています。運用時はログの監視が重要です。

- 冪等性
  - ETL の保存処理は upsert（ON CONFLICT DO UPDATE）や一意な ID を使うことで再実行可能にしています。

- セキュリティ / 安全
  - RSS 収集での SSRF 対策、defusedxml による XML パース、防御的な URL 正規化などの実装が含まれます。

---

## 主要ディレクトリ / ファイル構成

（ソースは `src/kabusys` 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースセンチメント解析（OpenAI）
    - regime_detector.py           -- 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得 + 保存）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - pipeline.py (ETLResult)      -- ETL 実行結果クラス
    - quality.py                   -- データ品質チェック
    - news_collector.py            -- RSS 収集 / 前処理 / 保存
    - calendar_management.py       -- 市場カレンダー管理（is_trading_day 等）
    - stats.py                     -- zscore_normalize 等統計ユーティリティ
    - audit.py                     -- 監査ログスキーマ生成・初期化
    - etl.py                       -- ETLResult の再エクスポート（簡易インターフェース）
  - research/
    - __init__.py
    - factor_research.py           -- momentum/value/volatility 等
    - feature_exploration.py       -- forward returns / IC / summary / rank
  - ai/...                         -- AI 関連ユーティリティ群
  - research/...                   -- 研究用ユーティリティ

---

## 開発 / 貢献

- コードはテストしやすい設計（API 呼び出し関数の差し替え / モックが可能）です。
- 大きな変更を行う場合はユニットテストと ETL のサンプル実行を追加してください。
- 外部 API 呼び出しのテストは実ネットワークに依存しないようモックして実行するのが推奨されます。

---

## ライセンス / 連絡先

（ここにライセンス情報やメンテナ連絡先を記載してください）

---

README は主要な使い方と設計意図をコンパクトにまとめています。必要に応じて実運用向けのデプロイ手順（systemd / cron / Airflow ジョブ化、監視・アラート設定など）や schema 初期化スクリプトを補足してください。