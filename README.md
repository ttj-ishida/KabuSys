# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなど、バックテスト・運用で必要とされる基盤機能を含みます。

主な設計方針
- ルックアヘッドバイアスを防ぐ（datetime.today()/date.today() を直接参照しない実装方針）
- DuckDB をデータストアとして利用（軽量・高速な分析向け）
- 外部 API 呼び出しは慎重にリトライやフェイルセーフを実装
- ETL・監査ログ・品質チェックは冪等性を意識して実装

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェックと型安全なラッパー（kabusys.config.settings）

- データパイプライン（kabusys.data）
  - J-Quants API クライアント（株価・財務・カレンダー取得）`jquants_client`
  - ETL パイプライン（差分取得・保存・品質チェック）`pipeline.run_daily_etl` 等
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS）`news_collector`
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化 / 管理（監査用 DuckDB）`audit.init_audit_db`

- 研究用モジュール（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ、Zスコア正規化

- AI（kabusys.ai）
  - ニュースセンチメントスコアリング（OpenAI を利用）`news_nlp.score_news`
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM）`regime_detector.score_regime`

- ユーティリティ
  - 統計ユーティリティ（zscore 正規化）
  - 設定（ログレベル・環境モード判定など）

---

## 必要環境 / 依存ライブラリ（例）

（プロジェクトの pyproject.toml / requirements.txt に合わせてください。以下は実行に必要となる主なライブラリ例です）

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例（開発環境）:
```bash
# 任意の仮想環境を作成してから
pip install duckdb openai defusedxml
# パッケージを editable インストールする場合（プロジェクトルートに pyproject.toml があることを想定）
pip install -e .
```

---

## 環境変数（主要）

kabusys は環境変数 / .env ファイルを使用します。プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。

主要なキー（必須のものはコード中で _require によりチェックされます）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可, デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の読み込み仕様
- 読み込み順: OS 環境変数 > .env.local > .env
- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt   # あれば
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成して必須キーを設定してください（例を以下に示します）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベース・監査 DB 初期化（必要に応じて）
   - 監査ログ専用 DB を初期化するには Python REPL やスクリプトで:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # :memory: も可
   # あるいは既存接続を渡して init_audit_schema を呼ぶことも可能
   ```

---

## 使い方（簡単な例）

※ ここでは最小限の使用例を示します。実運用ではエラーハンドリングやログ設定、ジョブスケジューラと組み合わせてください。

- ETL（日次パイプライン）の実行
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # today を基準に ETL を実行
print(result.to_dict())
```

- ニュースのスコア付け（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date: スコアを作る日（対象ウィンドウは前日15:00 JST～当日08:30 JST）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定（MA200 とマクロニュースの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- 監査スキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なモジュールと役割です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定ラッパー（settings）
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS/ニュース記事を集約して OpenAI に送信、ai_scores テーブルへ書き込み
    - regime_detector.py
      - ETF 1321 の MA200 とマクロニュースから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save）
    - pipeline.py
      - 日次 ETL の実装（run_daily_etl 等）
    - etl.py
      - ETLResult のエクスポート
    - news_collector.py
      - RSS からのニュース収集・正規化・保存
    - calendar_management.py
      - market_calendar 管理、営業日判定等
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL と初期化
  - research/
    - __init__.py
    - factor_research.py
      - momentum/value/volatility ファクター計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ・ランク関数
  - research/*（上記）

---

## 注意事項 / 補足

- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI（gpt-4o-mini）を使用します。API キーが必要です。
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ（失敗時はゼロスコア等）を内包していますが、コスト・レート制限に注意してください。

- 自動 .env ロード
  - config モジュールはプロジェクトルートを探索して `.env` / `.env.local` を自動読み込みします。CI／テスト環境で自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB の executemany に関する注意
  - 実装中に DuckDB のバージョン差分対策が入っており、空のパラメータで executemany を呼ばない等の注意点があります。ETL 内のチェックに従ってください。

- テスト
  - OpenAI や外部ネットワークを含む処理は、ユニットテスト時にモックすることを想定して設計されています（内部の _call_openai_api などを patch 可能）。

---

## 貢献 / 開発

- バグ・機能改善の PR を歓迎します。設計方針とルックアヘッドバイアス防止の考え方を尊重した変更をお願いします。
- 新しい外部依存を追加する場合は事前に議論してください（軽量性と再現性を重視）。

---

問題や実行に関する質問があれば、どの機能を使いたいか（ETL / ニューススコア / レジーム判定 / 監査初期化 等）を教えてください。具体的な実行コード例やトラブルシューティングをお手伝いします。