# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。J-Quants / kabuステーション / OpenAI 等と連携して、データのETL、品質チェック、ニュースNLP、市場レジーム判定、監査ログ（トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない設計が基本）
- DuckDB をデータレイクとして利用し、冪等保存（ON CONFLICT）を重視
- API 呼び出しはレート制御・リトライ・指数バックオフを実装
- ニュース収集は SSRF 等のセキュリティ対策を実装

---

## 機能一覧

- データ収集・ETL
  - J-Quants からの日次株価（OHLCV）/ 財務データ / 市場カレンダー取得（ページネーション対応、ID トークン自動更新）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、前日比スパイク、日付不整合チェック（quality.run_all_checks）
- ニュース収集 / 前処理
  - RSS フィード取得と前処理、トラッキングパラメータ除去、SSRF 対策（news_collector.fetch_rss / preprocess_text）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメントスコアを ai_scores テーブルへ書込（news_nlp.score_news）
- 市場レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.calc_*）
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブルと初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）
- カレンダー管理
  - 営業日判定 / 翌営業日・前営業日取得 / カレンダー更新ジョブ（data.calendar_management.*）

---

## 要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- openai
- defusedxml

（その他標準ライブラリの urllib, json, datetime 等を使用）

インストール例：
python -m pip install duckdb openai defusedxml

プロジェクトがパッケージ化されている場合は editable install:
pip install -e .

---

## 環境変数 / .env

このパッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします（既存 OS 環境変数 > .env.local > .env の優先順位）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（実運用で必要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（実行/発注に必要な場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用。関数呼び出し時に api_key を明示的に渡すことも可能）

データベースパス（省略可、デフォルトあり）:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト `data/monitoring.db`）

注意: 必須の環境変数が足りないと Settings プロパティが ValueError を送出します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン、プロジェクトルートへ移動
2. 依存パッケージをインストール
   pip install duckdb openai defusedxml
3. .env を作成（.env.example を参考に）
   - JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY などを設定
4. DuckDB ファイル用ディレクトリを用意（設定済みパスの親ディレクトリが自動作成される箇所もありますが、念のため）
5. （任意）KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑止

---

## 使い方（簡単な例）

※ ここでは最小構成の利用例を示します。実際はログ設定やエラーハンドリングを追加してください。

- 共通：DuckDB 接続と settings の利用
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）を実行して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用データベース初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- カレンダー / 営業日ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 注意点 / 実装上の特徴

- ルックアヘッドバイアス防止
  - 多くの関数が明示的な target_date を受け取り、内部で現在時刻を参照しないように設計されています（バックテスト用の安全設計）。
- 冪等性
  - J-Quants から取得したデータは save_* 関数で ON CONFLICT DO UPDATE により冪等保存。
  - news_collector は URL 正規化 + SHA256 ハッシュで記事 ID を生成して重複挿入を防ぐ。
- リトライ / レート制御
  - J-Quants クライアントは固定間隔スロットリングと再試行（指数バックオフ）を実装。
  - OpenAI 呼び出しもリトライ/バックオフを実装（news_nlp / regime_detector 内）。
- セキュリティ対策
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP ブロック）・受信サイズ制限・defusedxml を使用。
- テスト容易性
  - OpenAI 呼び出し内部関数はモック差し替えが容易になるように分離（ユニットテストで patch 可能）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP スコアリング（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py         — マーケットカレンダー管理
  - etl.py                         — ETL の公開インターフェース
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - quality.py                     — データ品質チェック
  - audit.py                       — 監査ログ初期化 / schema
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - news_collector.py              — RSS ニュース収集
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum, value, volatility）
  - feature_exploration.py         — 将来リターン / IC / summary
- (その他) strategy / execution / monitoring などパッケージ公開（__all__）

---

## 追加情報 / 開発メモ

- 自動で .env を読み込む仕組みがあるため、ローカルでの開発は .env に必要なトークン/キーを入れておくと便利です。自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI を使う部分はコストと利用制限に注意してください（バッチ処理時の並列度／バッチサイズを調整する必要があります）。
- DuckDB バージョン依存の注意点：一部の executemany の振る舞いや配列バインドに差異があるため、pipeline / news_nlp では互換性を考慮しています。

---

必要に応じて README に含めたい追加のサンプル（CI による ETL スケジューリング例、Dockerfile、.env.example のテンプレートなど）を作成できます。追加希望があれば教えてください。