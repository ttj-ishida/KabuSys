# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集とAIによるセンチメント評価、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針は「Look‑ahead bias の回避」「冪等性」「外部 API の堅牢なリトライ」「DuckDB を用いた軽量永続化」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数取得時のエラー提示
- データ ETL（J-Quants API）
  - 株価日足（OHLCV）取得・永続化（ページネーション・レート制御・リトライ）
  - 財務データ取得・永続化
  - JPX マーケットカレンダー取得・保存
  - 日次パイプライン（run_daily_etl）＋品質チェック
- ニュース収集
  - RSS 収集（URL 正規化、SSRF 防止、gzip/サイズ制限、トラッキング除去）
  - raw_news / news_symbols への冪等保存
- AI（OpenAI）連携
  - ニュースセンチメント: gpt-4o-mini を使った銘柄別 ai_score 生成（score_news）
  - 市場レジーム判定: ETF 1321 の MA200 乖離とマクロニュースセンチメントの合成（score_regime）
  - API エラー時のフォールバック / 再試行ロジック
- データ品質チェック（quality）
  - 欠損データ、スパイク、重複、日付不整合を検出
  - QualityIssue データクラスで詳細を収集
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター算出
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - 監査トレース用のスキーマ初期化（init_audit_schema / init_audit_db）

---

## 必要要件（想定）

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は上記をインストールしてください）

（プロジェクトに requirements.txt がある場合はそちらを参照してください。ここではコード中で使われている外部依存を列挙しています。）

---

## 環境変数

主要な環境変数（README で言及する主なもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う際に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

config モジュールはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の記法パーサはコメントやシングル/ダブルクォート、export 形式に対応しています。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. パッケージのインストール（編集可能なモード）
   - pip install -e .

5. 環境変数を準備
   - プロジェクトルートに `.env` を作成（.env.example を参照する想定）
   - 必須トークンやキーを設定してください。

---

## 使い方（簡単なコード例）

以下はライブラリを使った代表的な操作例です（DuckDB 接続は duckdb.connect を使用）。

- ETL（1日分のデータ取り込み + 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースの合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等への書き込み/クエリが可能
```

- カレンダー関連ユーティリティ

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## スキーマ初期化 / DB 周り

- ETL や保存関数は既存のテーブルを前提に動きます。スキーマ初期化用のユーティリティ（data.schema など）がある場合はそれを使ってください（本コードベース断片では audit の初期化ユーティリティが提供されています）。

- 監査ログ専用 DB の初期化:
  - init_audit_db(path) は親ディレクトリを自動作成し、UTC タイムゾーン固定でスキーマを作成します。

- デフォルトの DuckDB ファイル:
  - settings.duckdb_path → data/kabusys.duckdb

---

## テスト / 開発のヒント

- 環境変数自動読み込みはテストで邪魔になる場合があるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- OpenAI コール等はモジュール内の `_call_openai_api` を unittest.mock.patch で差し替え可能な設計です（news_nlp, regime_detector 共にテストフレンドリー）。
- RSS のネットワーク関連は `kabusys.data.news_collector._urlopen` をモックして制御できます。

---

## ディレクトリ構成（主なファイル）

省略可能・テスト用ファイルは除く、主要モジュールの概観:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント（ai_scores 生成）
    - regime_detector.py     -- 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py -- カレンダー管理（営業日判定等）
    - etl.py                 -- ETL の公開インターフェース（ETLResult 再エクスポート）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
    - quality.py             -- 品質チェック
    - audit.py               -- 監査ログスキーマ初期化
    - jquants_client.py      -- J-Quants API クライアント + 保存関数
    - news_collector.py      -- RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py     -- Momentum / Volatility / Value 等
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - research/* その他リサーチユーティリティ

---

## 注意事項 / 実運用のポイント

- OpenAI API（gpt-4o-mini）を利用する機能は API キーが必須であり利用料が発生します。テスト時はモック推奨。
- J-Quants API の利用にはレート制限や認証が必要です。get_id_token / _request にはリトライ・レート制御が組み込まれていますが、クォータ管理は運用側でも行ってください。
- DuckDB の executemany やバインドに関するバージョン差異に留意しています（空リストバインド回避など実装上の注意あり）。
- 監査ログは削除しない前提で設計されています。スキーマやタイムゾーン（UTC）に依存する部分があるため、既存 DB に導入する際は互換性を確認してください。
- 本ライブラリはバックテストや研究用途と実運用コード（発注）を分離する設計思想に基づいています。発注関連（kabu ステーション連携等）は別モジュールで実装する想定です。

---

必要であれば、README に含める具体的な .env.example や requirements.txt の例、あるいは CI/CD / デプロイ手順のテンプレートを追加できます。どの部分を詳細化しましょうか？