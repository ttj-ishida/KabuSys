# KabuSys

KabuSys は日本株のデータプラットフォームと研究・自動売買の基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）などを組み合わせて ETL、品質チェック、ニュースセンチメント、ファクター計算、監査ログ、発注監視までをサポートします。

主な目的は「ルックアヘッドバイアスを避けたデータ取得・前処理」「LLM を用いたニュースセンチメント」「研究用ファクター計算」「発注〜約定までの監査トレース」を低レイテンシかつ再現可能に実現することです。

---

## 機能一覧

- 環境設定管理
  - .env または環境変数から設定を読み込み（自動読み込みあり／無効化可能）
  - 必須設定のチェック（例: JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄一覧のページネーション対応取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB に冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次差分 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - バックフィル / バックテストに配慮した設計
  - ETL 実行結果を ETLResult として返却
- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出（閾値指定可）
  - QualityIssue を返却し、重大度（error/warning）で分類
- ニュース収集
  - RSS 取得・前処理（URL 正規化、トラッキング除去、SSRF 対策、gzip 対応）
  - raw_news / news_symbols への冪等保存想定
- ニュース NLP（LLM）
  - 銘柄ごとにニュースを統合して gpt-4o-mini でセンチメントを JSON で取得
  - バッチ（最大 20 銘柄）・リトライ・レスポンスバリデーションをサポート
- 市場レジーム判定（AI + テクニカル）
  - ETF（1321）200日 MA 乖離 + マクロニュース LLM センチメントを組合せて daily regime を判定・保存
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL・初期化
  - すべての監査イベントに UTC タイムスタンプを付与し冪等初期化可能
- 監視（SQLite）用パス提供（settings.sqlite_path）

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリで多くを実装しているため追加依存は最小限）

インストール例（pip）:
```
pip install duckdb openai defusedxml
# またはプロジェクト配布に合わせて
pip install -e .
```

requirements.txt がない場合は上記パッケージを適宜追加してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化
3. 依存をインストール（上記参照）
4. 環境変数を設定（.env 推奨）

推奨する .env の例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は主にライブラリを直接利用する Python スニペット例です。

- DuckDB 接続と ETL 実行（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルにアクセス
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {written} codes")
```

- 市場レジーム判定（regime score）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

- ファクター計算（研究）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

注意点:
- LLM を呼ぶ関数は api_key を引数に渡すか、環境変数 OPENAI_API_KEY を設定する必要があります。
- 各関数はルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない）になっています。バックテスト環境では target_date を明示して呼んでください。
- テスト時は内部の API 呼び出しヘルパ（例: _call_openai_api, _urlopen）をモックして外部依存を切り離せます。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出し用）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack 通知用チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するフラグ（値を設定すれば無効）

必須のキーが未設定だと Settings プロパティアクセス時に ValueError を投げます。

---

## テスト／モックのヒント

- OpenAI 呼び出しは各モジュール内でラップされており、テスト時は以下をパッチできます:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- RSS 取得やネットワークは kabusys.data.news_collector._urlopen をモックできます。
- ETL の id_token は引数で注入可能（id_token=None の場合は内部キャッシュ経由で自動処理）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス（自動 .env ロード、必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースセンチメント（銘柄単位）を LLM で算出し ai_scores に書込む
    - regime_detector.py
      - ETF MA200 とマクロニュース LLM を組合せて market_regime を判定
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理・営業日判定・calendar_update_job
    - pipeline.py
      - ETL のコア（prices/financials/calendar の差分取得、品質チェック）
    - etl.py
      - ETLResult のエクスポート（公開インターフェース）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付整合性）
    - audit.py
      - 監査ログ用 DDL と初期化（signal_events, order_requests, executions）
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py
      - RSS 収集、URL 正規化、テキスト前処理、SSRF 対策
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー、ランク変換
  - monitoring/  (コードベース内で監視用 SQLite を使う想定のファイル群が来る可能性あり)

（上記は現状の主要モジュールの要約です。細かなユーティリティ関数や定数は各ファイル内の docstring を参照してください。）

---

## ロギングと運用

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- 監査 DB は UTC タイムゾーン固定で記録されます（init_audit_schema は SET TimeZone='UTC' を実行）。
- カレンダー更新ジョブや ETL は冪等・再実行可能に設計されています。ジョブ化してスケジューラで運用することを推奨します。

---

この README はコードベースの概要をまとめたものです。各モジュールの詳細仕様・SQL スキーマ・外部 API の挙動については該当ソースファイルの docstring を参照してください（ソース内に豊富な設計コメントがあります）。ご希望があればセットアップ用のサンプル .env.example、運用ジョブ（cron/systemd）サンプルや Dockerfile / docker-compose のテンプレートも作成します。