# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究（ファクター計算）、監査ログ（約定トレース）などをワンパッケージで提供します。

主な設計方針
- バックテスト用の Look‑ahead バイアスを避ける（date/target_date を明示的に渡す設計）
- DuckDB を中心とした軽量かつ冪等性を意識した ETL / 保存処理
- 外部 API 呼び出しにはリトライ・レート制御・フェイルセーフを組み込み
- 監査ログ（signal → order_request → execution）の完全トレースをサポート

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート判別）および必須チェック（kabusys.config）
- データ取得 / ETL（kabusys.data）
  - J-Quants からの日次株価・財務・上場情報の取得（jquants_client）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（calendar_management）
  - ニュース収集（RSS）と前処理（news_collector）
  - データ品質チェック（quality）
  - 汎用統計ユーティリティ（stats）
  - 監査ログ（signal / order_request / executions）スキーマ作成・初期化（audit）
- AI（kabusys.ai）
  - ニュースのセンチメント集約（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime） — ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター要約

---

## セットアップ手順

前提
- Python 3.10+（型注釈に union types 等を使用しているため）
- ネットワークアクセス（J-Quants, OpenAI, RSS）

1. リポジトリをクローン／プロジェクトを取得
   - (例) git clone …

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - このコードベースで利用される主な依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意し、そこからインストールしてください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（OS環境変数が優先）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN ・・・ J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD      ・・・ kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN        ・・・ Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID       ・・・ Slack チャンネル ID（必須）
   - OPENAI_API_KEY         ・・・ OpenAI API キー（LLM を使う処理で必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト INFO）
     - KABUS_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

   例 .env
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

※ 実行前に上記の環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLU（記事 -> 銘柄ごとの ai_score 書き込み）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か引数で指定
print("書き込み銘柄数:", n_written)
```

- 市場レジームスコアの計算
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルで持つことを推奨 (例: data/audit.duckdb)
audit_conn = init_audit_db("data/audit.duckdb")
```

- 設定の参照例
```python
from kabusys.config import settings
print(settings.env, settings.log_level, settings.duckdb_path)
```

注意点
- OpenAI 呼び出しで API エラーが発生した場合、モジュール内でフェイルセーフ（0.0 として扱う等）が多く実装されていますが、APIキーは必須です（関数によっては引数で渡せます）。
- KABUSYS_ENV が `live` の場合は実際の発注等と連携する前提の処理があります。テストは `development` または `paper_trading` で行ってください。

---

## ディレクトリ構成

主要なファイル／モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save 系）
    - pipeline.py         — ETL パイプライン（run_daily_etl など）
    - etl.py              — ETL の公開インターフェース（ETLResult）
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py   — RSS ニュース拾い上げ
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログテーブル初期化/DB作成
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 計算
    - feature_exploration.py — 将来リターン, IC, summary 等
  - research/*           — ファクター研究用ユーティリティ

（実際のリポジトリは pyproject.toml / setup.py / requirements.txt がある想定です）

---

## 開発・運用メモ

- .env 自動読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - 読み込み優先順は OS 環境 > .env.local > .env
  - テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ロギング / 環境
  - settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
  - settings.env は development / paper_trading / live のいずれかで、live は実運用モードの意味合いを持ちます。

- テスト
  - モジュール設計上、外部 I/O（HTTP や OpenAI 呼び出し）は差し替え可能（関数をモック）にしてあり、ユニットテストでのモックが容易です。
  - news_nlp と regime_detector は外部呼び出しラッパーを内部で分離しているため単体テストが可能です。

---

## 参考・問い合わせ

不明点や拡張が必要な点があれば、リポジトリの Issue に記載してください。README の補足や API ドキュメント化（docstrings からの自動生成）を推奨します。

--- 

以上。README の追加・修正やサンプルスクリプトの作成も対応できます。必要な出力形式（例えば英語版、短縮版、別ファイル分割など）があれば指示してください。