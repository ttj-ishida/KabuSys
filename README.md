# KabuSys

日本株向けの自動売買 / データパイプライン用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログスキーマなど、研究・運用で必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分フェッチして DuckDB に保存
  - 差分取得・バックフィル・品質チェックを含む日次 ETL パイプライン
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース関連
  - RSS 取得・前処理（SSRF 対策／トラッキング除去）
  - ニュース -> 銘柄紐付け、raw_news への保存ロジック
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）生成
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントで日次レジーム（bull/neutral/bear）を算出
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター要約、Zスコア正規化
- 監査（Audit）スキーマ
  - シグナル → 発注要求 → 約定までのトレーサビリティ用テーブル定義と初期化ユーティリティ
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と Settings API

---

## 要件（依存ライブラリ）

主な依存（実際の pyproject / requirements を参照してください）:
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ: urllib, json, datetime 等）

※ テスト時や軽量環境では一部モジュールをモックして利用できます。

---

## セットアップ

1. リポジトリをクローン / ソースを入手

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv && source .venv/bin/activate

3. インストール（開発編集可能モード）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時）
     - SLACK_BOT_TOKEN — Slack 通知（必要な場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必要な場合）
     - KABU_API_PASSWORD — kabuステーション API パスワード（運用時）
   - 任意:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env の簡易例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（サンプル）

以下は主要な処理を Python から呼び出す例です。各関数は DuckDB 接続を受け取り、外部副作用は明確です。

- DuckDB に接続して日次 ETL を実行する例

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は今日が使用されます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）を実行する例

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# target_date: スコア生成日（ニュースウィンドウは前日15:00JST～当日08:30JST）
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジーム判定を実行する例

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化（監査専用 DB を作る例）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# init_audit_db は初期化済みの duckdb 接続を返します
```

- カレンダー系ユーティリティ例

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。関数呼び出し時に api_key 引数で渡すことも可能です。
- LLM 呼び出しはリトライやフォールバックロジックを持ち、API失敗時には 0.0 を返すなどのフェイルセーフが組み込まれています。

---

## ディレクトリ構成（主要ファイルのみ）

- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数 / .env 自動ロード / Settings
    - ai/
      - __init__.py
      - news_nlp.py — ニュースセンチメント（ai_scores）生成
      - regime_detector.py — 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py — J-Quants API クライアント / 保存ロジック
      - pipeline.py — ETL パイプライン（run_daily_etl 等）
      - etl.py — ETLResult 再エクスポート
      - calendar_management.py — 市場カレンダー管理・ユーティリティ
      - news_collector.py — RSS 取得・前処理・raw_news 保存ロジック
      - quality.py — データ品質チェック（QualityIssue）
      - stats.py — Zスコア正規化など統計ユーティリティ
      - audit.py — 監査ログスキーマ定義・初期化
    - research/
      - __init__.py
      - factor_research.py — モメンタム / バリュー / ボラティリティ計算
      - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - その他（execution, monitoring, strategy などの名前空間は将来拡張想定）

---

## 注意事項 / 運用上のポイント

- Look-ahead bias に注意
  - 多くのモジュールは明示的に datetime.today() を参照しない設計です。バックテストで使用する場合は対象日以前のデータのみで処理されることを保証してください。
- OpenAI / J-Quants の API レート制限に注意
  - J-Quants: レート制御とリトライ実装あり
  - OpenAI: news_nlp / regime_detector はリトライ／バックオフを実装していますが、利用側でも適切なスロットリングを推奨します
- テスト用の差し替えポイント
  - news_nlp._call_openai_api / regime_detector._call_openai_api は unittest.mock.patch 等で差し替え可能です
- .env 自動読み込み
  - プロジェクトルート（.git / pyproject.toml を基準）を自動検出して .env / .env.local を読み込みます。自動読み込みを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DuckDB の executemany 空リスト挙動
  - 一部 DuckDB バージョンでは executemany に空リストを渡すとエラーになるため、コード側で空チェックを行っています。DuckDB のバージョン違いによる仕様差異に注意してください。

---

## トラブルシューティング

- OpenAI へのリクエストが失敗する
  - OPENAI_API_KEY が設定されているか確認。テスト時は API 呼び出しをモックすることを推奨。
- J-Quants 認証エラー（401）
  - JQUANTS_REFRESH_TOKEN の有効性を確認。jquants_client は 401 を検出するとトークンを自動リフレッシュして再試行します。
- RSS 取得で SSRF / private host による拒否
  - news_collector はリダイレクト先やホストがプライベートアドレスの場合にブロックします。外部 RSS を利用する際は公開ホストを指定してください。

---

この README は主要な使い方・設計方針をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。開発・運用に関する質問や README の補足が必要であれば教えてください。