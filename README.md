# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・LLM を用いたニュースセンチメント解析・市場レジーム判定・研究用ファクター計算・監査ログ（トレーサビリティ）などを包含します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを基準に探索）
  - 必須設定の取得と検証を提供（kabusys.config.settings）

- データ ETL / Data Platform
  - J-Quants からの差分取得（株価日足、財務データ、JPX カレンダー）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day など）
  - ニュース収集（RSS → raw_news、SSRF / 容量制限 / トラッキング除去）
  - 監査ログ（signal / order_request / execution テーブル群）の初期化ユーティリティ

- AI（LLM）連携
  - ニュース単位で銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に保存（news_nlp.score_news）
  - マクロニュース + ETF（1321）の 200 日 MA 乖離を組み合わせて市場レジーム（bull/neutral/bear）を判定し market_regime に保存（regime_detector.score_regime）
  - API 呼び出しはリトライ、フェイルセーフ設計（API 失敗時は 0.0 をフォールバックする等）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリー（research.feature_exploration）
  - 汎用 Z-score 正規化ユーティリティ（data.stats.zscore_normalize）

- 外部連携周辺
  - J-Quants クライアント（レート制限、トークンリフレッシュ、ページネーション対応）
  - kabuステーション（発注）や Slack 通知などの設定を想定した設定項目を準備

---

## 必要条件（推奨）

- Python 3.10+（型アノテーションの union 等を利用）
- 必要なパッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （その他ユーティリティを追加する場合あり）

プロジェクトの pyproject.toml / requirements.txt を参照してください（リポジトリに含まれる想定）。

---

## 環境変数（主な設定）

プロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる想定のキー（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に使用）

その他オプション
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG, INFO, ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）

設定は `from kabusys.config import settings` で取得できます。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   （プロジェクトが PEP 517/pyproject を使っている前提なら）
   ```
   pip install -e .
   ```
   または requirements.txt がある場合:
   ```
   pip install -r requirements.txt
   ```

4. `.env` を作成して必要な環境変数を設定
   - `.env.example` を参考に必須キーを設定してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=secret
     ```

5. DuckDB データベース用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単なコード例）

以下は主要なコンポーネントの利用例です。実運用ではログ設定や例外処理を適切に追加してください。

- 日次 ETL を実行（DuckDB 接続）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", written)
```

- 市場レジーム判定（OpenAI API キーは環境変数または引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を env に設定しておく
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))

# Zスコア正規化例
normed = zscore_normalize(momentum, columns=["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降は conn を使って監査テーブルへ書き込む処理を行う
```

---

## 重要な設計上の注意点

- ルックアヘッドバイアス対策:
  - モジュールの多くは内部で `datetime.today()` や `date.today()` を参照しない設計です（操作の対象日を明示する API を採用）。
  - ETL / スコアリング関数には target_date を渡して使用してください。

- フェイルセーフ設計:
  - LLM/API 呼び出し失敗時は極力例外を投げずにフォールバック（例: マクロセンチメント = 0.0）して処理継続します。ただし API キー未設定等、致命的な前提欠落は例外となります。

- DuckDB 互換性:
  - 一部の実装は DuckDB のバージョン差（executemany の空リスト扱い等）に対応するための注意が含まれています。

---

## ディレクトリ構成

概略（重要ファイルのみを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの LLM によるセンチメント解析
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult のエクスポート
    - news_collector.py              — RSS ニュース収集・前処理
    - calendar_management.py         — 市場カレンダー管理（営業日判定等）
    - stats.py                       — 汎用統計ユーティリティ（zscore）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum, value, volatility）
    - feature_exploration.py         — forward returns, IC, summary 等

---

## テスト / 開発上のヒント

- OpenAI やネットワーク依存部分はテストでモック化することを想定して実装されています（例: _call_openai_api, _urlopen などを patch）。
- 自動 .env ロードを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB はインメモリモード(":memory:") でも初期化関数を利用できます（audit.init_audit_db など）。

---

本 README はコードベースの主要な機能と利用方法の概要です。詳細な API 仕様や運用手順（CI/CD、発注フロー、Slack 通知設定、監視/アラート設計等）は別途ドキュメント（Design Docs / Operation Guide）を参照してください。