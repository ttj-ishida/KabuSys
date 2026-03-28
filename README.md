# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants / Kabuステーション / RSS / OpenAI を組み合わせて、データ取得（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- データ取得・ETL（J-Quants から株価・財務・カレンダーを取得して DuckDB に保存）
- ニュース収集および LLM によるセンチメントスコアリング（gpt-4o-mini を想定）
- 市場レジーム判定（MA200 とマクロニュースセンチメントの合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ：シグナル → 発注 → 約定までのトレーサビリティを保持するスキーマ管理

設計上の特徴:
- Look-ahead バイアス防止のため、内部処理は明示的な target_date を受け取り現在時刻を直接参照しない実装になっています。
- DuckDB を主な永続ストレージとして想定。
- OpenAI（Chat Completions / JSON mode）を利用した NLP 呼び出しはリトライとフォールバック処理を備えています。
- ETL / 保存処理は基本的に冪等（ON CONFLICT / DO UPDATE 等）で実装。

---

## 主な機能一覧

- kabusys.data
  - jquants_client: J-Quants API 呼び出し（取得・保存・認証・レート制御・リトライ）
  - pipeline / etl: 日次 ETL パイプライン（calendar / prices / financials）と ETL 結果型
  - news_collector: RSS からのニュース収集と前処理（SSRF 防止、gzip 限度、ID 生成）
  - calendar_management: JPX カレンダー管理 / 営業日判定関数（is_trading_day, next_trading_day 等）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査用テーブルの DDL と初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア等）
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM でセンチメントを算出、ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に記録
- kabusys.research
  - factor_research: momentum / value / volatility 等の計算
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー等

---

## 環境変数（主要）

config.py で環境変数から設定を読み込みます。必須/任意を明記します。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（プロジェクトで Slack を使う場合）
- SLACK_CHANNEL_ID: Slack 送信先チャネルID
- KABU_API_PASSWORD: kabuステーション API パスワード（発注を行うモジュールを使う場合）
- OPENAI_API_KEY: OpenAI API を使う機能（score_news / score_regime）を実行する場合は必須（これ自体は明示的に指定するか関数引数で注入可能）

任意（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 任意で自動 .env ロードを無効化（1 をセット）

自動ローディング:
- プロジェクトルートに .env / .env.local がある場合、起動時に自動で読み込みます（CWD ではなく __file__ を基準に探索）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（開発環境）

※リポジトリに requirements.txt / pyproject.toml がある想定で一般的な手順を示します。必要なパッケージはソース内で利用されているため最低限下記パッケージが必要です。

必要 Python バージョン:
- Python 3.10 以上（Union 型記法 Path | None 等を利用）

推奨手順:

1. 仮想環境作成・有効化
   - unix/mac:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージをインストール
   - 代表的なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）
   - pip install -r requirements.txt
   - または: pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env` を作成し、上記の必須変数を設定します。
   - 自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ作成（任意）
   - デフォルトの DuckDB 保存先は data/kabusys.duckdb です。`data/` ディレクトリを作成しておくとよいです。

---

## 使い方（基本例）

以下はライブラリの主要な使い方サンプルです。実行前に必要な環境変数（特に API キー）を設定してください。

1) 日次 ETL 実行（DuckDB に接続して日次 ETL を回す例）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored codes: {count}")
```

3) 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または api_key 引数
```

4) 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可能
```

5) リサーチ用ファクター計算
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意事項:
- OpenAI 呼び出しはネットワークおよび料金が発生するため注意して実行してください。
- テスト時はモジュール内の _call_openai_api 等をモックすることが推奨されています（各モジュールの docstring に記載あり）。
- ETL / API 呼び出しはリトライ／レート制御が入っていますが、APIキーやトークンの管理は利用者側で行ってください。

---

## ディレクトリ構成（主なファイル・モジュール）

（src/kabusys 以下の主要構成）
- __init__.py
  - パッケージ公開: data, strategy, execution, monitoring（strategy 等は将来拡張想定）
- config.py
  - 環境変数読み込み・設定管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py: ニュースセンチメント解析と ai_scores 書き込み
  - regime_detector.py: MA200 とマクロニュースの合成で market_regime を算出
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得 + DuckDB へ保存）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 収集・前処理・raw_news 保存
  - calendar_management.py: 市場カレンダー管理 / 営業日判定
  - quality.py: データ品質チェック（QualityIssue 定義）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py: モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py: 将来リターン・IC・統計サマリー等

（上記以外にも strategy / execution / monitoring 等のトップレベル API が将来存在する想定）

---

## 開発・テスト時のヒント

- OpenAI 呼び出しやネットワーク依存部分はユニットテストでモックすること。各モジュール内で _call_openai_api 等を分離しているため patch しやすくなっています。
- DuckDB はシングルファイル DB のためローカル開発で簡単に扱えます。テストでは :memory: を使うと便利です。
- ETL は部分失敗を許容しつつログで報告する設計です。品質チェックの結果（QualityIssue）を見て手動で対応を検討してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の検出）を基準に行います。CI 等で異なる挙動にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください。

---

## ライセンス・貢献

（このテンプレートではライセンスファイルは含まれていません。実プロジェクトでは LICENSE を追加してください）

貢献方法や Issue / PR ポリシーはリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。

---

README は以上です。必要であれば導入手順を OS ごとに詳述したり、CLI やシステムd タスクのサンプル、docker-compose 例などを追加できます。どの情報を優先して追記しましょうか？