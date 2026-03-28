# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（発注/約定トレーサビリティ）などをモジュール化しています。

主な設計方針は「バックテストでのルックアヘッドバイアス排除」「冪等性」「API 呼び出しのフェイルセーフ／リトライ」「DuckDB によるローカル永続化」です。

---

## 機能一覧

- データ収集 / ETL
  - J-Quants API からの株価（日足）、財務情報、JPX カレンダー取得（ページネーション・レートリミット・リトライ対応）
  - 差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS フィードからのニュース収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores への書き込み）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + LLM センチメント）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリーユーティリティ
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査テーブル作成・初期化ユーティリティ
  - 監査DB（DuckDB）初期化関数
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須環境変数のラップ（settings オブジェクト）

---

## 必要条件

- Python >= 3.10
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

2. 依存パッケージをインストールします（例）:

   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定します。プロジェクトルートに `.env` を置くと自動的に読み込まれます（.env.local で上書き可）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env の例:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション（注文API）パスワード
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI (ニュース NLP / レジーム判定)
   OPENAI_API_KEY=sk-...

   # Slack (通知など)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境種別
   KABUSYS_ENV=development  # development | paper_trading | live

   # ログレベル
   LOG_LEVEL=INFO
   ```

4. （任意）DuckDB ファイルの親ディレクトリが存在しない場合は作成されますが、手動で `data/` を作っておくと安心です。

---

## 使い方（簡単な例）

以下はライブラリをプログラムから利用する際の代表的な例です。すべて Python スクリプト内で実行できます。

- 設定参照

```python
from kabusys.config import settings

print(settings.duckdb_path)       # Path('data/kabusys.duckdb')
print(settings.is_dev)            # True / False
token = settings.jquants_refresh_token  # 必須: なければ ValueError
```

- 日次 ETL の実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores への書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
print(f"written {n_written} scores")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DB（監査テーブル）の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# 返り値は初期化済みの duckdb connection
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト: {"date": ..., "code": "...", "mom_1m": ..., ...}
```

注意:
- OpenAI を使う関数は api_key 引数を受け取ります。None なら環境変数 `OPENAI_API_KEY` を参照します。
- ETL / ニュース / レジーム判定はそれぞれ DB の所定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を参照／更新します。初期スキーマが必要な場合は別途スキーマ初期化機能（プロジェクト内に存在する schema 初期化関数）を実行してください（このリポジトリ内では audit の初期化ユーティリティが提供されています）。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

設定は .env / .env.local / OS 環境変数の順に適用されます（OS 環境変数が最優先）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP（ai_scores 生成）
    - regime_detector.py            -- 市場レジーム判定（ma200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得＆DuckDB 保存）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult の再エクスポート
    - news_collector.py             -- RSS ニュース収集
    - calendar_management.py        -- マーケットカレンダー管理・営業日判定
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 統計ユーティリティ（zscore 正規化等）
    - audit.py                      -- 監査ログテーブルの初期化
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum, volatility, value）
    - feature_exploration.py        -- 将来リターン / IC / 統計サマリー / rank
  - その他（strategy / execution / monitoring）へのエクスポートプレースホルダ

（実際のリポジトリにはさらに補助モジュールやテスト等が存在する場合があります）

---

## 開発メモ / 注意点

- DuckDB のバージョン依存や executemany の挙動（空リスト不可）に注意した処理が含まれています。
- OpenAI 呼び出しはリトライ＆フェイルセーフ（失敗時はスコアを 0.0 にフォールバック）を組み込んでいます。テスト時は内部の _call_openai_api をモックして挙動を制御できます。
- news_collector では SSRF 対策（ホストのプライベート判定、リダイレクト検査）、XML の安全パーサ（defusedxml）を用いています。
- audit 初期化は transactional オプションあり。DuckDB のトランザクション特性に注意してください（ネストトランザクションは不可）。

---

## サポート / 貢献

バグ報告や機能提案は Issue を作成してください。コード貢献は PR を歓迎します。README の内容は実装側の更新に合わせて随時整合性を取る必要があります。

---

以上。必要であれば README に含めるサンプル .env.example や詳細なスキーマ初期化手順、運用上のワークフロー（定期バッチ例、Slack 通知の使い方など）を追加で作成します。どのセクションを拡張しますか？