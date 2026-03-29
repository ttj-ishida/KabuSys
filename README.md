# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集・NLP（OpenAI）によるセンチメント評価、リサーチ用ファクター計算、監査ログ（オーディット）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤機能をモジュール化した Python ライブラリです。主に以下を提供します：

- J-Quants API を用いた株価・財務・カレンダー等の差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- JPX マーケットカレンダー管理と営業日ロジック
- RSS によるニュース収集と記事の前処理（SSRF・ZIP爆弾対策等を考慮）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（銘柄別 ai_scores, 市場レジーム判定）
- 研究用モジュール：ファクター計算、将来リターン、IC、Zスコア正規化等
- 監査ログ（signal → order_request → execution のトレーサビリティ）向けのスキーマ初期化ユーティリティ
- 環境変数管理ユーティリティ（.env 自動読み込み機能）

設計上、ルックアヘッドバイアスを避けるために「現在時刻を内で呼ばない」ことや、DB 書き込みは冪等性（ON CONFLICT / DELETE→INSERT など）を重視しています。

---

## 主な機能一覧

- data/etl.py: 日次 ETL パイプライン（run_daily_etl） — 株価・財務・カレンダー取得、品質チェック
- data/jquants_client.py: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
- data/news_collector.py: RSS 収集、URL 正規化、SSRF 対策、raw_news への保存ロジック
- data/calendar_management.py: 市場カレンダーの判定・前後営業日検索
- data/quality.py: 欠損・重複・スパイク・日付不整合チェック
- data/audit.py: 監査ログスキーマ作成 & 初期化（監査テーブル・インデックス）
- research/*: ファクター計算・特徴量解析・統計ユーティリティ
- ai/news_nlp.py: 銘柄ごとのニュースセンチメントを取得して ai_scores に書き込む（OpenAI）
- ai/regime_detector.py: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- config.py: .env 自動読み込み（プロジェクトルート検出）と settings オブジェクト（必須環境変数の取得）

---

## 必須環境変数（例）

このライブラリはいくつかの外部 API キーや設定を環境変数から取得します。最低限以下を設定してください（README の例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector のデフォルト）
- （オプション）KABUSYS_ENV: development / paper_trading / live
- （オプション）LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- （オプション）KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト時等）

.env のサンプル例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
# データベースパス（省略時は data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

config.py はプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を自動で読み込みます（環境変数が優先、.env.local は .env を上書き）。

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 表記や | 型を使用しています）
- Git でプロジェクトをチェックアウト済み

1. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   実際の運用では追加でログ周りやテストフレームワーク、Slack SDK 等が必要になる可能性があります。プロジェクトに requirements.txt があればそちらを使用してください。

3. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置く
   - 必須の API キーや設定を上記のキーで設定する

4. DuckDB ファイルの準備
   - デフォルト DB パス: `data/kabusys.duckdb`（settings.duckdb_path）
   - 監査用 DB を別途初期化する場合は `kabusys.data.audit.init_audit_db(path)` を使用

5. （任意）監査スキーマ初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(settings.duckdb_path)  # もしくは別のパス
   # conn は duckdb の接続オブジェクト
   ```

---

## 使い方（簡単なコード例）

以下はライブラリの代表的なユースケースと呼び出し例です。DuckDB 接続は duckdb.connect(path) で作成します。

- ETL（日次パイプライン）の実行:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（銘柄別、OpenAI 必須）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API key は環境変数 OPENAI_API_KEY
print(f"Scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュース合成）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（別 DB に分けたい場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 環境設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)     # Path オブジェクト
print(settings.env)             # development / paper_trading / live
print(settings.is_live)
```

注意点:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。関数呼び出しの引数で api_key を渡すことも可能です。
- ETL / API 呼び出しは外部ネットワークを使用するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD や unittest.mock.patch 等で外部依存を差し替えてください。
- DuckDB の executemany に空リストを渡せないバージョン（例: 0.10）に配慮した実装になっています。

---

## 主要モジュールと責務（簡易ディレクトリ構成）

src/kabusys/
- __init__.py (バージョン定義)
- config.py — 環境変数読み込み / Settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py — 銘柄ごとのニュースセンチメント取得（OpenAI バッチ）
  - regime_detector.py — 市場レジーム判定（1321 MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETL の公開インターフェース（ETLResult など）
  - news_collector.py — RSS 収集・記事の保存
  - calendar_management.py — マーケットカレンダーと営業日ユーティリティ
  - quality.py — データ品質チェック（QualityIssue）
  - stats.py — 汎用統計ユーティリティ（Zスコア正規化等）
  - audit.py — 監査ログスキーマ初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- monitoring, strategy, execution, などのパッケージ名は __all__ に含まれているが、実装はここに含まれている範囲に依存します（将来的機能）。

（リポジトリには上記以外にもヘルパーが多数存在します。README の目的に合わせて主要部分を要約しています）

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアスに注意: ライブラリの多くは target_date の未満・以前といった条件でデータ取得を行い、バックテストや研究でのリークを避ける設計になっています。関数は内部で date.today() を参照しない設計が原則です（ただし ETL のデフォルトは現在日）。
- API キー管理: 本番では .env ファイルではなく安全なシークレットストレージ（Vault 等）を利用してください。`.env` の自動読み込みはテスト時に無効化可能です。
- 冪等性: J-Quants 保存関数や audit 初期化などは冪等性を考慮して実装されています。DB 書き込みはトランザクションを使っている箇所がありますが、DuckDB の特性に注意してください（ネストトランザクション不可等）。
- エラーハンドリング: ニュース NLP や OpenAI 呼び出しはフェイルセーフ設計（失敗時は 0.0 にフォールバック等）になっています。運用時はログ・監視を整備してください。
- ログレベル: LOG_LEVEL と KABUSYS_ENV を適切に設定して運用してください。

---

## 開発 / テストヒント

- 自動 .env 読み込みは config.py によって行われます。テストでは環境を汚染しないために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- OpenAI 呼び出しやネットワークリクエストはモックしやすいように内部呼び出し関数が直接ラップされています（例: news_nlp._call_openai_api, regime_detector._call_openai_api, news_collector._urlopen など）。unittest.mock.patch で差し替えてテスト可能です。
- DuckDB はインメモリ `":memory:"` での接続をサポートしているため、テスト時はファイルを作らずに済ませることができます。

---

必要があれば、用途別（ETL の Cron 設定例、監査 DB のバックアップ方法、Slack 通知実装サンプルなど）に具体的な使い方・運用手順を追記します。どの部分を詳しく知りたいか教えてください。