# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアント、マーケットカレンダー管理、品質チェック、LLM を用いたニュースセンチメント評価などを提供します。

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- 市場データ（株価・財務・マーケットカレンダー）の差分 ETL（J-Quants API 経由）
- ニュース収集（RSS）と LLM によるニュースセンチメント算出（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA 乖離 + マクロニュースセンチメント）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）および研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- J-Quants API クライアント（レートリミット・リトライ・トークン更新）
- 環境変数・設定の安全な読み込み（.env / .env.local の自動ロード）

設計方針として、ルックアヘッドバイアスを防ぐために関数は内部で日時を自律的に決めず、呼び出し側が基準日を渡すことを前提にしています。また、外部 API 失敗時は安全側のフォールバックを行い、部分失敗でも他データを保護する実装（冪等保存や個別 DELETE→INSERT 等）を採用しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants からのデータ取得 & DuckDB への冪等保存
  - pipeline / etl: 日次 ETL（市場カレンダー・株価・財務）の実行（差分取得 + 品質チェック）
  - calendar_management: JPX カレンダー取得・営業日判定ユーティリティ
  - news_collector: RSS から記事取得・前処理・raw_news 保存（SSRF 対策・サイズ制限など）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル定義と初期化ユーティリティ
  - stats: zスコア正規化などの汎用統計関数
- ai
  - news_nlp.score_news: ニュースを LLM に渡して銘柄別スコアを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースで市場レジーム判定を行い market_regime に保存
- research
  - factor_research: calc_momentum / calc_volatility / calc_value（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（研究用ユーティリティ）
- config: .env の自動読み込み・設定ラッパー（settings オブジェクト）

---

## 必要要件 / 依存パッケージ

最低限必要な主要パッケージ（抜粋）:

- Python 3.9+
- duckdb
- openai (OpenAI の Python クライアント)
- defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカル開発インストールする場合:
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## 環境変数 / 設定

KabuSys はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（読み込み順: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要なら）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視関連
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

設定の読み取りは `from kabusys.config import settings` で行います（例: settings.jquants_refresh_token）。

例 .env（最低限）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール（上記参照）
3. プロジェクトルートに `.env`（および `.env.local`）を作成して必要な環境変数を設定
4. DuckDB 用のディレクトリを作成（デフォルトでは data/ にファイルを作成）
   - 例: mkdir -p data
5. 初期スキーマ（監査DB など）を作る場合は init 関数を利用

---

## 使い方（代表的な例）

以下は Python REPL またはスクリプト内で使う簡単な例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を用意して日次 ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合 api_key 引数は省略可
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定を行う:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- calendar_management のユーティリティ利用例:

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
- LLM 呼び出し（news_nlp / regime_detector）は OpenAI の API を呼びます。API キーと利用コストに注意してください。
- J-Quants 呼び出しはレート制限（120 req/min）を守る実装ですが、API 認証情報と利用ポリシーに従ってください。

---

## 実運用上の注意点

- .env 読み込みの優先順位: OS > .env.local > .env。テストで自動読み込みをオフにするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- ETL 実行はネットワーク・API エラーに対して堅牢化されていますが、API クォータや料金に注意してください。
- LLM レスポンスの不確実性に備え、news_nlp/regime_detector は失敗時にゼロフォールバックやスキップする設計です。ログを確認してください。
- DuckDB を共有で使う場合は排他やトランザクションに注意（DuckDB の動作特性に依存）。
- audit テーブルは監査用途のため削除せず保存することが前提です。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルとモジュール（src 配下）:

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他 ETL / schema 関連)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring / execution / strategy / etc. (パッケージ化のための __all__ 等で公開)

各ファイルは README の各セクションで説明した責務を持ちます（DB スキーマやテーブル名についてはソース内の docstring を参照してください）。

---

## ロギング / デバッグ

- 設定は環境変数 `LOG_LEVEL` で制御できます（例: LOG_LEVEL=DEBUG）。
- 各モジュールは標準 logging を利用しており、詳しい情報はログに出力されます。

---

## 貢献 / テスト

- 既存の設計方針に沿って、新規モジュールや変更を加える場合はルックアヘッドバイアスや冪等性（IDempotency）に配慮してください。
- テストでは .env 自動ロードを無効にするか、モジュールの関数をモックして外部 API への依存を切ることを推奨します。

---

この README は現時点のソースコードに基づく概要説明です。詳細な実装や追加ユーティリティの使用方法は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README にコマンドライン例やさらに詳しいセットアップ手順を追記します。