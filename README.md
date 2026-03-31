# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ群です。J-Quants / kabuステーション / OpenAI 等と連携して、データ取得（ETL）、品質チェック、ニュースNLP による銘柄スコアリング、マーケットレジーム判定、監査ログ（オーディット）などを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## 概要

KabuSys は以下の主要コンポーネントを持ちます。

- data: J-Quants からのデータ取得・保存（DuckDB への ETL）、カレンダー管理、ニュース収集、品質チェック、監査ログ初期化など。
- ai: OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析と、市場レジーム判定。
- research: ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ。
- config: 環境変数/設定の読み込みユーティリティ（.env 自動読み込み機能付き）。
- その他: 統計ユーティリティなど。

設計方針として、ルックアヘッドバイアスを防ぐために date.today()/datetime.today() を不用意に参照しない設計、API 呼び出しに対するリトライ・フェイルセーフ、DuckDB を用いた冪等保存（ON CONFLICT）などを採用しています。

---

## 主な機能一覧

- ETL パイプライン（data.pipeline）
  - 日次 ETL（株価、財務、カレンダー）の差分取得と保存
  - 品質チェック（欠損・重複・スパイク・日付整合性）
  - 結果を ETLResult オブジェクトで返却

- J-Quants クライアント（data.jquants_client）
  - 株価日足、財務データ、上場銘柄情報、JPX カレンダー取得（ページネーション対応）
  - レート制御・リトライ・トークン自動リフレッシュ機構
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）

- 市場カレンダー管理（data.calendar_management）
  - 営業日判定、前後営業日の検索、期間内営業日取得、夜間更新ジョブ

- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、SSRF 対策、raw_news / news_symbols への冪等保存設計

- ニュース NLP（ai.news_nlp）
  - OpenAI を用いた銘柄ごとのニュースセンチメント（ai_scores）生成
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ

- レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM センチメントを重み合成して market_regime に記録

- 監査ログ（data.audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ（DuckDB）
  - UUID ベースのトレーサビリティ設計

- 研究用ユーティリティ（research）
  - モメンタム/ボラティリティ/バリュー計算、将来リターン、IC 計算、ファクターサマリー等

---

## 必要条件 / 推奨

- Python 3.10 以上（Union 型の | 演算子を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, datetime, json など

（プロジェクトの配布方法に合わせて requirements.txt / pyproject.toml を用意してください。）

インストール例（最低限の依存を pip で）:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

config.Settings が環境変数から各種設定を参照します。プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます（起動時の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主に必要となる環境変数（一例）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuapi のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"

.env の例（機密情報は実際の値で置き換えてください）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=Cxxxxxxx
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発用）

1. Python 環境を用意（3.10+ 推奨）
2. 依存ライブラリをインストール
   ```
   python -m pip install duckdb openai defusedxml
   ```
3. リポジトリをクローンして作業ディレクトリへ移動
4. プロジェクトルートに `.env`（あるいは `.env.local`）を作成して必要な環境変数を設定
5. DuckDB の初期スキーマ準備や監査DB初期化が必要な場合はサンプルコード参照

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続と日次 ETL の実行:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコアリング:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", count)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

注意点:
- OpenAI API を用いる機能（score_news, score_regime）は OPENAI_API_KEY が必要です。
- J-Quants API を用いる ETL は JQUANTS_REFRESH_TOKEN が必要です。
- 各関数はルックアヘッドバイアスを避ける設計になっており、target_date を明示して呼び出すことを推奨します。

---

## ディレクトリ構成（主要ファイルの説明）

概略:

- src/kabusys/
  - __init__.py: パッケージ定義、公開サブパッケージ一覧
  - config.py: 環境変数/.env 読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメント解析（score_news）
    - regime_detector.py: 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（fetch / save）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - etl.py: ETLResult の再エクスポート
    - calendar_management.py: 市場カレンダー管理、更新ジョブ
    - news_collector.py: RSS 収集と前処理
    - quality.py: データ品質チェック
    - stats.py: 汎用統計ユーティリティ（zscore_normalize）
    - audit.py: 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py: ファクター計算（モメンタム、ボラ、バリュー）
    - feature_exploration.py: 将来リターン、IC、統計サマリー等

（上記以外の細かいユーティリティ関数は各モジュール内部にあります）

---

## 動作上の注意 / 運用メモ

- .env 自動ロード:
  - プロジェクトルート (.git または pyproject.toml を探す) を基準に .env/.env.local を自動読み込みします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env

- DuckDB への executemany:
  - 一部の関数は DuckDB の executemany の制約を考慮して空リストを渡さないようにしています。

- エラー処理:
  - API 呼び出しにはリトライとフェイルセーフを組み込んでいます（大部分は失敗時にスキップして継続する挙動）。
  - ETL の各ステップは独立して例外処理され、完了結果にエラー概要と品質チェックの結果を含めます。

- セキュリティ:
  - news_collector は SSRF 対策（ホストのプライベート判定、リダイレクト検査）や defusedxml による XML 安全処理を行っています。

---

## 貢献 / 開発

- 新機能追加や修正は module 単位でテストを追加してください。AI モジュールや外部 API を呼ぶ部分はモックを使った単体テストが推奨されます（例: _call_openai_api の差し替え）。
- schema 変更時は data.audit の init_audit_schema を参照して DDL を更新してください。

---

この README はコードベース（src/kabusys 以下）に基づいて作成しています。さらに具体的な導入手順（CI/CD、Docker 化、運用監視、Slack 通知の実装など）が必要であれば、目的に合わせて別途追記可能です。