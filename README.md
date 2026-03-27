# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants / DuckDB を中心にデータ取得・ETL・品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログなどを提供します。

---

## 主な概要

- データ取得（J-Quants API）と DuckDB への保存（冪等）
- 日次 ETL パイプライン（価格 / 財務 / カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP による銘柄単位センチメント算出（OpenAI 使用）
- マクロセンチメントと ETF MA を合成した市場レジーム判定
- リサーチ向けファクター計算・IC / 統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- Slack 通知・kabuステーション周りの設定を想定（設定管理あり）

---

## 機能一覧

- kabusys.config
  - 環境変数読み込み（.env / .env.local の自動ロード、無効化フラグあり）
  - 必須設定チェック（例: JQUANTS_REFRESH_TOKEN 等）

- kabusys.data
  - jquants_client: J-Quants API クライアント、取得・保存関数（daily_quotes / financials / calendar / listed info）
  - pipeline: 日次 ETL 実行（run_daily_etl）・個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 取得・前処理・保存（SSRF 対策・gzip 上限・トラッキング除去等）
  - calendar_management: 営業日判定・次営業日/前営業日・カレンダー更新ジョブ
  - audit: 監査ログ用スキーマ初期化 / 専用 DB 初期化（init_audit_schema / init_audit_db）
  - stats: Zスコア正規化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントの取得と ai_scores への書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを合成した市場レジーム判定

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize による正規化

---

## セットアップ手順（開発 / 実行環境構築）

前提: Python 3.10+ を推奨（型アノテーションに union 型などを使用）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要なパッケージをインストール
   基本的に以下をインストールしてください（requirements.txt があればそれを使ってください）。
   ```
   pip install duckdb openai defusedxml
   ```
   - 追加で必要になれば環境に応じた HTTP クライアントやテストツールを入れてください。

4. パッケージとしてインストール（開発モード）
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.cfg 等がある場合）

5. 環境変数の準備
   - プロジェクトルートに `.env`（と任意で `.env.local`）を置くと、自動でロードされます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード（利用する場合）
- SLACK_BOT_TOKEN : Slack 通知に使う bot token（利用する場合）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

その他:
- OPENAI_API_KEY : OpenAI を使う機能（news_nlp, regime_detector）を実行する場合
- KABUSYS_ENV : 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...)

データベースのデフォルトパス（環境変数で変更可能）:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB 等; デフォルト: data/monitoring.db)

例: `.env.example`
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

## 使い方（主要 API / 実行例）

以下は Python REPL やスクリプト内で使うサンプルコードです。

- DuckDB 接続を開く例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n}")
```

- 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ用ファクター計算（calc_momentum など）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

- データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- news_nlp と regime_detector は OpenAI API を使用します。API 呼び出しはリトライやフェイルセーフを備えていますが、OpenAI API キー（OPENAI_API_KEY）が必要です。
- ETL / データ保存は DuckDB に対する SQL 実行を行います。既にテーブルスキーマが存在することを前提とする部分があります（schema 初期化は別モジュールで管理想定）。

---

## .env 自動ロードの挙動

- パッケージ読み込み時にプロジェクトルートを .git または pyproject.toml を基準に探索し、見つかった場合はそのルートの `.env`（先に読み込み）および `.env.local`（上書き）を自動で読み込みます。
- OS 環境変数は上書きされません（.env は未設定キーのみ設定）。`.env.local` は既存の OS 環境変数を保護しつつ上書きできます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（抜粋、主要ファイル／モジュールを表示）

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
      - audit.py
      - stats.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/  (コードベースに参照がある想定)
    - strategy/    (戦略層は別途実装想定)
    - execution/   (注文実行 / broker 接続は別モジュールで想定)

その他:
- pyproject.toml / setup.cfg / requirements.txt 等（存在する場合）
- .env.example（プロジェクトルートに置くことを推奨）

---

## 運用上の注意

- Look-ahead バイアス防止: 多くの関数は内部で date.today() を直接参照しない設計になっています。バックテスト時は対象日を明示的に渡してください。
- API 呼び出しにはレート制限・リトライロジックが組み込まれていますが、実運用では API 利用上限を監視してください（J-Quants / OpenAI）。
- DuckDB に対する executemany の振る舞いやバージョン差異に注意しています（空リスト渡し回避など）。
- ニュース収集は SSRF 等の脅威に注意して安全対策（スキーム検査・プライベートホスト検査・受信サイズ上限）を実装していますが、運用時も定期的に監視してください。

---

## 参考 / 連絡

不具合報告・機能要望は issue を立ててください。設計上の疑問・拡張要望は README に追記します。

--- 

以上。必要があればサンプル .env.example、requirements.txt、簡易スクリプト（etl_runner.py）などのテンプレートを作成します。どれを優先しますか？