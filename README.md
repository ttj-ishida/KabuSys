# KabuSys

日本株向け自動売買 / データプラットフォーム コンポーネント群。

このリポジトリはデータ取得（J-Quants）、データ品質チェック、特徴量算出、ニュースNLP（OpenAI を利用したセンチメント）、市場レジーム判定、監査ログ（発注→約定トレース）など、自動売買システムの基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける設計（関数内で date.today() を直接参照しない等）
- DuckDB を一次データストアとして利用
- 外部 API（J-Quants / OpenAI）呼び出しに対する堅牢なリトライとフェイルセーフ
- ETL / 品質チェックは冪等性・部分失敗耐性を考慮

---

## 機能一覧

- 環境設定読み込み（.env ファイル / 環境変数）
  - 自動ロード：プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込み
  - 無効化フラグ：KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- データ収集・ETL（kabusys.data）
  - J-Quants クライアント（株価・財務・マーケットカレンダー取得）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキング除去）
  - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル初期化
  - init_audit_schema / init_audit_db（冪等・UTC保存）

- 研究・特徴量（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
  - クロスセクション Zスコア正規化（kabusys.data.stats.zscore_normalize）

- AI（kabusys.ai）
  - ニュースセンチメント算出（score_news）
  - 市場レジーム判定（score_regime）: ETF(1321)のMA乖離とマクロニュースのLLMセンチメントを合成
  - OpenAI 呼び出しは堅牢にリトライ・パース検証

---

## 必要条件 / 依存パッケージ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml

例（pip）:
```
pip install duckdb openai defusedxml
```

プロジェクト配布があれば requirements.txt / pyproject.toml を使用してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効化する場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   代表的な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

3. DuckDB データベースの準備
   - デフォルトは settings.duckdb_path（例: data/kabusys.duckdb）。
   - 監査ログ専用 DB を初期化する場合は init_audit_db を使用（下記参照）。

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから呼び出す例です。事前に環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）を設定してください。

- ETL を日次で実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で指定
print("written:", n_written)
```

- 市場レジーム判定を実行（market_regime テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn を使って監査テーブルにアクセスできます
```

- 市場カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- AI モジュール（score_news / score_regime）は OpenAI API を呼び出します。APIキーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- これらの関数はルックアヘッドを避ける実装になっていますが、バックテスト等で使用する際はデータの取得時刻管理（fetched_at）と開始日設定に注意してください。

---

## .env 自動読み込みの振る舞い

- 起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索します。
- 見つかれば `.env` をまず読み込み（既存の OS 環境変数は上書きされない）、続けて `.env.local` を上書きモードで読み込みします（OS 環境変数保護あり）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

.env のパースはシェル形式（export あり・クォート・コメント処理）に対応しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                - ニュースセンチメント算出（OpenAI）
    - regime_detector.py         - 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                - ETL パイプライン / run_daily_etl 等
    - etl.py                     - ETL インターフェース再エクスポート
    - calendar_management.py     - マーケットカレンダー管理（営業日判定等）
    - news_collector.py          - RSS ニュース収集（SSRF / トラッキング除去 対策）
    - quality.py                 - データ品質チェック
    - stats.py                   - 統計ユーティリティ（zscore 正規化等）
    - audit.py                   - 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py         - モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py     - 将来リターン / IC / 統計サマリー 等

---

## 運用上の注意 / ベストプラクティス

- 本コードは実運用の一部を想定しています。実際の発注・口座接続を行う場合は十分なテストを行ってください。
- OpenAI や J-Quants の API 呼び出しはコスト・レート制限が存在します。バッチ化・適切なキー管理を行ってください。
- ETL 実行・DB 書き込みは冪等性を考慮していますが、バックアップやバージョン管理を推奨します。
- log レベルは環境変数 LOG_LEVEL で制御します。

---

README に記載されていない詳細は各モジュールの docstring を参照してください。追加で README に載せたい内容（例: CI/CD、テスト実行方法、開発ワークフロー等）があれば教えてください。