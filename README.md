# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants / kabu ステーション等からのデータ収集・ETL、ニュースの NLP/LLM によるセンチメント評価、ファクター計算、監査ログ（オーディット）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（コード内で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を中心とするローカル DB ベースの ETL と品質チェック
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP / 市場レジーム判定（フォールバック・リトライ実装あり）
- 冪等性を重視した DB 保存（ON CONFLICT / トランザクション）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（無効化可）
  - 設定値は `kabusys.config.settings` 経由で取得

- データ ETL（jquants_client）
  - J-Quants API から日足（OHLCV）、財務データ、カレンダー等を差分取得・保存
  - レート制御・リトライ・トークン自動リフレッシュ対応

- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合チェック

- ニュース収集（data.news_collector）
  - RSS 取得・前処理・SSRF対策・トラッキングパラメータ除去・冪等保存

- ニュースNLP / LLM（ai.news_nlp, ai.regime_detector）
  - 銘柄別ニュースセンチメント算出（gpt-4o-mini + JSON mode）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定

- リサーチ（research）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - zscore 正規化ユーティリティ

- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - 監査用 DuckDB 初期化関数を提供

---

## 要求環境・依存ライブラリ

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# 開発用: pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```

2. 必要パッケージをインストールします（例）:
   ```bash
   python -m pip install -U pip
   python -m pip install duckdb openai defusedxml
   # またはパッケージを編集可能インストール:
   # python -m pip install -e .
   ```

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   必要な主要環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - OPENAI_API_KEY=<openai_api_key>
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB ファイル等のディレクトリを作成（必要に応じて）:
   ```bash
   mkdir -p data
   ```

---

## 使い方（例）

以下は主要な利用パターンのサンプルです。適宜ロギング設定やエラーハンドリングを追加してください。

- DuckDB 接続を作り日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルに接続
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を実行（target_date を指定しないと今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコア算出:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター算出（モメンタム等）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って order_requests 等の監査テーブルにアクセス可能
```

- 設定値を参照する:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI API 呼び出しを行う関数は api_key 引数を受け取りますが、None の場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / LLM 呼び出しは外部 API を呼ぶためネットワークと API キーが必要です。テスト時はモックを使用してください（コード内にもモックしやすい実装あり）。

---

## ディレクトリ構成（抜粋）

この README は提供されたコードベースに基づくものです。主要ファイルを抜粋して示します。

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
      - quality.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - audit.py
      - etl.py (wrapper re-export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/  (パッケージは __all__ に入っていますが実装がある場合はここに)
    - execution/   (約定・発注関連の実装を置く想定)
    - strategy/    (戦略定義を置く想定)

---

## 開発上の注意点 / 実装ポリシー（要約）

- ルックアヘッドバイアス防止のため、関数は明示的に target_date を受け取り内部で現在日時に依存しない設計になっています。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT 等）で行います。部分的失敗があっても既存データを不必要に削除しない設計です。
- 外部 API 呼び出し（J-Quants, OpenAI）はリトライと指数的バックオフを備え、フェイルセーフ（失敗時に 0 またはスキップして継続）を多用しています。運用ではログを監視してください。
- ニュース収集では SSRF 対策・XML の安全パース・レスポンスサイズ制限を実装しています。

---

必要に応じて README の拡張（CI、テスト実行方法、コマンドラインツールの使い方等）を作成します。追加で含めたい情報（例: 実行スクリプト、docker-compose、サンプル .env.example の完全版など）があれば教えてください。