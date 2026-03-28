# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants API からのデータ取得（株価・財務・カレンダー）・ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（オーダー／約定トレーサビリティ）などの機能を含みます。

---

## 主な機能

- データ収集・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集 / 前処理
  - RSS フィード収集、URL 正規化、SSRF 対策、記事の前処理、raw_news への冪等保存
- AI（OpenAI）連携
  - ニュースのセンチメント分析（銘柄別、バッチ処理、JSON Mode）
  - マクロニュース + ETF MA 乖離に基づく市場レジーム判定（bull / neutral / bear）
  - API 呼び出しはリトライ・バックオフを備えフェイルセーフ設計
- 研究 / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー、Z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - UUID ベースのトレーサビリティ、冪等キー設計、UTC タイムスタンプ
- ユーティリティ
  - マーケットカレンダー管理（営業日判定等）
  - J-Quants API クライアント（レート制御、トークンリフレッシュ、ページネーション）
  - DuckDB への保存関数（冪等）

---

## 必要条件（概略）

- Python 3.10+
- 外部ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）

（実際の requirements はプロジェクトの packaging / requirements ファイルに従ってください）

---

## セットアップ

1. リポジトリをクローン／取得し、仮想環境を作成して有効化します。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストールします（例）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※ 実プロジェクトでは `pip install -e .` や `pip install -r requirements.txt` を使用してください。

3. 環境変数の準備:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただしテストや特殊な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須の環境変数や推奨値は次項を参照してください。

---

## 環境変数（主なもの）

以下は本ライブラリで参照される主な環境変数（大文字）です。`.env.example` を参照して `.env` を作成してください。

- 認証・API
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード（実行系で使用）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

- Slack（通知等）
  - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID: 通知先チャネル ID（必須）

- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

- 実行設定
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

注意:
- 一部関数は引数で API キーや id_token を直接渡せます（テストや分離実行に便利）。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易コード例）

以下は主要なユースケースの簡単な呼び出し例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の取得（例）

```python
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのセンチメント（銘柄別）を計算して ai_scores に書き込む

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていること
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

- 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# OpenAI key は env の OPENAI_API_KEY か api_key 引数で指定
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用 DB）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
```

- Audit スキーマを既存 conn に適用

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点:
- AI モジュール（news_nlp / regime_detector）は OpenAI 呼び出しを行います。テスト時は内部の _call_openai_api をモックして実行してください（README 内のコード・コメント参照）。
- run_daily_etl 等は内部で calendar の調整を行います。ETL は複数ステップで例外を捕捉しつつ処理を継続します。結果は ETLResult にまとめられます。

---

## ディレクトリ構成（主要ファイル説明）

（プロジェクトのソースは `src/kabusys` 配下にあります）

- src/kabusys/__init__.py
  - パッケージ定義、公開サブパッケージの列挙

- src/kabusys/config.py
  - 環境変数読み込み・設定取得用 Settings クラス
  - .env 自動読み込み機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

- src/kabusys/data/
  - jquants_client.py
    - J-Quants API クライアント（認証、リトライ、ページネーション、保存関数）
  - pipeline.py
    - ETL パイプライン（run_daily_etl、run_prices_etl 等）
    - ETLResult データクラス
  - quality.py
    - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - news_collector.py
    - RSS 収集、前処理、SSRF 対策
  - calendar_management.py
    - 市場カレンダー管理（営業日判定、次営業日 / 前営業日、calendar_update_job）
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize）
  - audit.py
    - 監査ログ（DDL・初期化・init_audit_db）

- src/kabusys/ai/
  - news_nlp.py
    - 銘柄別ニュースセンチメント算出（gpt-4o-mini、バッチ処理、検証）
  - regime_detector.py
    - ETF(1321) の MA とマクロニュースを合成して市場レジーム判定
  - __init__.py
    - score_news のエクスポート等

- src/kabusys/research/
  - factor_research.py
    - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー
  - __init__.py
    - 研究用 API の再エクスポート

- その他
  - data/audit / monitoring 用の SQLite 関連パスは設定で指定可能

---

## 開発・テストのヒント

- 環境変数自動ロードを無効化する:
  - テストで環境汚染を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しのモック:
  - テスト時は news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch で差し替えることを想定しています。
- DuckDB の executemany の挙動:
  - 一部の関数では DuckDB のバージョン依存の制約（executemany に空リストを渡せない等）に対する対処があります。テスト時は注意してください。

---

## ライセンス / 貢献

（この README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE ファイルを含めてください）  

バグ報告・プルリクエスト歓迎です。貢献の際はテストとドキュメントを添えてください。

---

この README はコードベース内の docstring / モジュール設計をもとにまとめたものです。より詳細な設計や実運用の設定（プロダクション用認証、発注フロー、リスク管理ポリシー等）は別途設計書を参照してください。