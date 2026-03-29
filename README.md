# KabuSys

KabuSys は日本株のデータ基盤・研究・AI評価・監査ログを備えた自動売買/リサーチ用ライブラリのコア実装です。本リポジトリは主に以下を提供します。

- J-Quants API からのデータ ETL（株価・財務・市場カレンダー）
- DuckDB を用いたデータ保存・品質チェック・監査テーブル初期化
- ニュース収集（RSS）と OpenAI を使ったニュース NLP（銘柄別センチメント）
- 市場レジーム判定（MA と マクロニュースセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 汎用ユーティリティ（統計・カレンダー判定等）

注意: この README は与えられたソースツリーの内容に基づく簡易ドキュメントです。strategy / execution / monitoring 等の上位レイヤは本スナップショットに含まれない場合があります。

---

## 主な機能（抜粋）

- データ ETL
  - run_daily_etl: 市場カレンダー取得 → 株価/財務差分取得 → 品質チェック
  - 差分取得・バックフィル、ページネーション対応、冪等保存（ON CONFLICT）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token (refresh token から id_token を取得・キャッシュ)
  - レート制限とリトライ（バックオフ）を実装
- ニュース
  - RSS 取得（SSRF/プライベートアドレス・gzip・サイズ上限対策）
  - raw_news 保存、news_symbols との紐付け（実装は保存ロジックに依存）
- AI
  - score_news: 指定ウィンドウのニュースを銘柄ごとに集約して OpenAI でセンチメント評価（gpt-4o-mini）
  - score_regime: ETF (1321) の 200 日 MA 乖離 と マクロニュースセンチメントを合成して市場レジーム判定
  - 再試行・失敗時のフェイルセーフ（LLM失敗時は 0.0 へフォールバック 等）
- 研究（Research）
  - calc_momentum, calc_value, calc_volatility: ファクター群の計算（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic, factor_summary, rank: 特徴量評価・IC 計算・サマリー
  - zscore_normalize: クロスセクションの Z スコア正規化
- データ品質チェック
  - 欠損 / 重複 / スパイク / 日付不整合 の検出（QualityIssue を返す）
- 監査ログ（Audit）
  - 監査用テーブル定義（signal_events / order_requests / executions）と初期化関数
  - init_audit_db: 監査専用 DuckDB 初期化ユーティリティ

---

## セットアップ手順

前提
- Python >= 3.10（型注釈に `X | None` を使用）
- git, virtualenv 等の基本ツール

例: 仮想環境作成と依存パッケージ（代表的なもの）

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# 代表的な依存:
pip install duckdb openai defusedxml
# 開発用にパッケージをインストールする場合（プロジェクトルートで）
pip install -e .
```

環境変数
- 本ライブラリは複数の必須・任意環境変数を参照します。主なもの:

必須（モジュール利用に応じて）
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（ETL/クライアント）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID - Slack 通知（必要な場合）
- KABU_API_PASSWORD - kabuステーション API のパスワード（発注等を行う場合）
- OPENAI_API_KEY - OpenAI API キー（score_news / score_regime 等を使う場合）

任意/デフォルト有り
- KABUSYS_ENV - development / paper_trading / live （デフォルト development）
- LOG_LEVEL - DEBUG/INFO/…（デフォルト INFO）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH - 監視 DB（デフォルト data/monitoring.db）

.env
- ルートディレクトリに `.env` / `.env.local` を置くと自動で環境変数を読み込みます（package 内の config モジュールがプロジェクトルートを .git または pyproject.toml から探します）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（テンプレートは .env.example を参照）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は代表的な操作の使い方サンプルです。実行は Python スクリプトまたはインタラクティブに行えます。

1) DuckDB 接続を用意して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) OpenAI を使ってニュースをスコアリング（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に入っていれば api_key を省略可能
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

3) 市場レジームを判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査 DB 初期化（audit テーブルの作成）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
```

5) 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

6) RSS を取得して記事オブジェクトに変換（news_collector.fetch_rss）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- AI 関連（score_news/score_regime）は OpenAI の API を利用します。API キーと通信料に注意してください。
- DuckDB のスキーマ（テーブル群）は ETL 実行や監査初期化の関数群が期待する形式である必要があります。既存プロジェクトに接続する際はスキーマ整合を確認してください。
- データ取得/保存は冪等性、リトライ、レート制御を組み込んでありますが、実運用時はログ・監視・エラー処理の追加を推奨します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは Python パッケージ `kabusys` として `src/kabusys` 下に実装されています。主要ファイルと役割は以下の通りです。

- src/kabusys/__init__.py
  - パッケージ初期化、バージョン定義
- src/kabusys/config.py
  - 環境変数管理・自動 .env ロード・settings オブジェクト
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄別に集約して OpenAI でセンチメント評価（score_news）
  - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - pipeline.py: ETL 実装、run_daily_etl 等
  - jquants_client.py: J-Quants API クライアント（fetch/save 関数）
  - news_collector.py: RSS 収集・前処理
  - quality.py: データ品質チェック（欠損/重複/スパイク/日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - etl.py: ETLResult の再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py: calc_momentum/calc_value/calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

（上記は本リポジトリ内の主要モジュールを抜粋した一覧です）

---

## 運用上の注意

- 環境変数が必須の箇所は config.Settings のプロパティで _require によりチェックされ、未設定時は ValueError が発生します（.env.example の参照推奨）。
- LLM / 外部 API 呼び出しはネットワーク障害・レート制限に対してリトライ設計されていますが、コスト・レイテンシに注意してください。
- DuckDB と SQL クエリは日付や NULL の扱いに厳密なので、ETL 実行前にスキーマと既存データの整合性確認を推奨します。
- news_collector は RSS のサイズ上限・SSRF 対策・gzip 対応等を備えています。外部ソースを追加する際はソースの信頼性を評価してください。

---

## さらに読む / 開発

- 各モジュール上部の docstring に設計方針・処理フロー・注意点が記載されています。実装や拡張を行う際はまず該当モジュールの docstring を確認してください。
- テスト・CI 設定はこのスナップショットに含まれていないため、ローカルでユニットテストを追加してから運用に移すことを推奨します。

---

もし README に追加したい具体的な実行例（cron 用スクリプト、Dockerfile、requirements.txt の候補など）があれば教えてください。それらを含めたより詳細なドキュメントを作成します。