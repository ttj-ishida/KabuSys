# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB を用いたデータレイク、J-Quants からの ETL、ニュースの NLP スコアリング（OpenAI）、
市場レジーム判定、監査ログ（発注 → 約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（クイックスタート / API 例）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・ファクター計算・AI によるニュースセンチメント評価・市場レジーム判定・監査ログといった機能を備えたライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API を使った株価・財務・カレンダーの差分 ETL（DuckDB へ保存）
- RSS からのニュース収集と OpenAI（gpt-4o-mini 等）による銘柄別 NLP スコアリング
- ファクター計算（モメンタム、バリュー、ボラティリティ）と研究用ユーティリティ
- 市場レジーム（bull / neutral / bear）判定（ETF + マクロニュースの合成）
- 発注〜約定までの監査ログスキーマ（DuckDB）と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - ニュース収集（RSS、SSRF/サイズ保護、正規化、news → news_symbols）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログのスキーマ初期化 / 専用 DB 初期化
  - 汎用統計ユーティリティ（Zスコア正規化など）
- ai/
  - news_nlp: ニュースを銘柄別にまとめて OpenAI に投げ、ai_scores を生成
  - regime_detector: ETF の MA200 乖離とマクロニュースセンチメントを合成して market_regime を生成
- research/
  - ファクター計算（momentum / value / volatility）
  - 特徴量解析（forward returns, IC, summary, rank）

---

## 必要条件

- Python 3.9+
- 推奨ライブラリ（一部は必須）
  - duckdb
  - openai (OpenAI の Python SDK)
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging など）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または開発用: pip install -e .
```

※ プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージを設置
2. 仮想環境を作る（推奨）
3. 必要パッケージをインストール（上の「必要条件」参照）
4. 環境変数を設定（.env をプロジェクトルートに置くか、OS 環境変数を設定）
   - パッケージの設定モジュールは自動でプロジェクトルートの .env / .env.local を読み込みます。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. DuckDB ファイルなどストレージ先のディレクトリを用意（settings.duckdb_path の親ディレクトリ）

---

## 環境変数（.env）

以下は主要な環境変数の一覧例（.env.example を用意することを想定）:

- JQUANTS_REFRESH_TOKEN=xxxxx         # J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD=xxxxx             # kabuステーション API パスワード（必須）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=xoxb-...            # Slack 通知用（必須なら設定）
- SLACK_CHANNEL_ID=C0123456           # Slack 通知先チャンネル（必須なら設定）
- DUCKDB_PATH=data/kabusys.duckdb      # DuckDB ファイルパス（デフォルト）
- SQLITE_PATH=data/monitoring.db       # 監視用 SQLite（設定が必要なら）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY=sk-...                # OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1      # 自動 .env 読み込みを無効化する場合

注意:
- settings（kabusys.config.Settings）は上記の環境変数を参照して値を公開します。
- 必須キーが不足すると Settings プロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## 使い方（クイックスタート / API 例）

以下は最小限の使用例です。実行前に必要な環境変数を設定してください。

共通: DuckDB に接続する例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI API 必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date に対して前日 15:00 JST 〜 当日 08:30 JST に該当する raw_news をスコア化
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 MA200 とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
# market_regime テーブルに挿入されます
```

4) 監査ログ（発注/約定）用の DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログテーブルにアクセスできます
```

5) ファクター / 研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

---

## ディレクトリ構成（主要ファイルと簡単な説明）

（パッケージのルートは src/kabusys 以下を想定）

- src/kabusys/__init__.py
  - パッケージのバージョン / エクスポートの定義
- src/kabusys/config.py
  - 環境変数読み込み・設定管理（.env 自動読み込みロジック、Settings クラス）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄ごとに集約して OpenAI へ送り ai_scores テーブルへ保存
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースで市場レジームを判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（認証・取得・保存・リトライ・レート制御）
  - pipeline.py: ETL パイプライン（run_daily_etl など）と ETLResult
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 取得・正規化・保存（SSRF 対策、サイズ制限）
  - calendar_management.py: market_calendar の管理・営業日判定・更新ジョブ
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログテーブル DDL / 初期化ユーティリティ
- src/kabusys/research/
  - __init__.py
  - factor_research.py: モメンタム / ボラティリティ / バリューの算出
  - feature_exploration.py: 将来リターン計算 / IC / 統計サマリー / ランク関数

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアス回避
  - 多くの関数は内部で datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を与える設計です。バックテスト等でデータリークを防ぐための配慮があります。
- 冪等性
  - J-Quants からの保存関数は ON CONFLICT / DO UPDATE を使用し冪等に動作します。
  - ニュースは URL 正規化 → SHA256（先頭32文字）で ID を作ることで重複保存を抑制します。
- フェイルセーフ
  - AI/API 呼び出しで失敗した場合は例外をそのまま投げずフォールバックする箇所（macro_sentiment=0.0 など）があります。ログを確認してください。
- セキュリティ対策
  - news_collector は SSRF 防止のためホスト/リダイレクト先のチェック、レスポンスサイズ制限、XML パースに defusedxml を利用しています。
- テスト容易性
  - OpenAI や HTTP 呼び出し箇所はモック可能な内部関数を提供しており、単体テストが書きやすい設計です。

---

必要であれば README に含めるサンプル .env.example、requirements.txt、簡易 CLI スクリプト（etl_run.py など）のテンプレートも作成できます。どの内容を追加希望か教えてください。