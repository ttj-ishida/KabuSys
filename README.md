# KabuSys

日本株向けのデータプラットフォーム & 自動売買リサーチ基盤（プロトタイプ実装）

このリポジトリは、J-Quants API や RSS ニュース、OpenAI（LLM）などを組み合わせて
データ収集（ETL）、品質チェック、ニュースの NLP スコアリング、ファクター計算、
市場レジーム判定、および監査ログ（発注→約定のトレーサビリティ）を行うための
Python モジュール群です。

主な設計方針:
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を無闇に使わない）
- DuckDB を中心としたローカルデータ保存と SQL ベース処理
- IDempotency（ON CONFLICT / 冪等保存）やリトライ・レート制御の実装
- 外部 API 呼び出しにはリトライ・バックオフ、フェイルセーフ（失敗時は無効化して継続）を適用
- セキュリティ対策（RSS の SSRF 防止、XML の defusedxml 使用 等）

バージョン: 0.1.0

---

## 機能一覧

- データ収集（ETL）
  - J-Quants から株価日足（OHLCV）／財務データ／JPX カレンダーを差分取得（ページネーション対応）
  - 差分取得、バックフィル、DuckDB への冪等保存
- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、重複チェック、日付整合性チェック
- ニュース収集
  - RSS フィードから記事収集、テキスト前処理、raw_news / news_symbols へ保存（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI）
  - 銘柄単位に記事を集約して LLM によりセンチメントスコア（ai_scores）を生成
  - レート制限・リトライ・レスポンス検証・スコアクリップを実装
- 市場レジーム判定（AI + MA）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成し日次で bull/neutral/bear を判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等ファクター算出
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
  - すべての操作を UUID でトレース可能にする設計

---

## 必要条件 / 依存パッケージ

推奨 Python バージョン: 3.10 以上（型注釈に `|` のユニオンを使用）

主な依存ライブラリ（例）
- duckdb
- openai
- defusedxml

（実際の requirements.txt/pyproject.toml はプロジェクトに応じて用意してください）

---

## 環境変数（主な設定）

このパッケージは .env ファイル（プロジェクトルート）および OS 環境変数を読み込みます。
自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知用トークン（本コード内では設定のみ）
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI:
- OPENAI_API_KEY — news_nlp / regime_detector が利用（関数呼び出し時に引数で渡すことも可能）

その他（デフォルトあり／任意）:
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 (.env):
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成:
   python -m venv .venv
   source .venv/bin/activate

2. 依存パッケージをインストール:
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）

3. プロジェクトルートに `.env` を配置し、必要な環境変数を設定。

4. DuckDB ファイルの準備:
   - デフォルトは data/kabusys.duckdb に保存されます（settings.duckdb_path）
   - audit 用 DB を初期化する場合は後述のスクリプト参照

---

## 使い方（主要ユースケース）

以下は簡単な Python スニペット例です。適宜 logging 設定や例外処理を加えてください。

- DuckDB 接続を作成して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を利用）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
print(f"書込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
```

- 研究用ファクター算出（例: モメンタム）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

- 監査ログスキーマの初期化（audit DB を独立して作る例）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # Path や ":memory:" が可能
# conn は初期化済み DuckDB 接続
```

---

## 実装上の注意 / 補足

- Look-ahead bias 回避:
  - AI / ETL 処理の多くは target_date を明示的に渡し、内部で現在日時を参照しないようになっています。バックテストや再現性のために target_date を厳密に指定してください。

- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini 等を用いて JSON Mode で結果を受け取り、レスポンス検証・クリップを行います。
  - テスト時は内部の _call_openai_api をモックして API 呼び出しを置き換えられます。

- J-Quants クライアント:
  - RateLimiter（120 req/min）・自動トークンリフレッシュ（401 時にリトライ）・ページネーション対応・保存は ON CONFLICT DO UPDATE により冪等に実装。
  - `get_id_token()` は settings.jquants_refresh_token を利用します。

- ニュース収集:
  - RSS の取得は SSRF 対策・最大受信サイズ制限・トラッキングパラメータ除去・XML の安全パーサ（defusedxml）を利用。
  - 記事IDは正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を保持。

---

## ディレクトリ構成（主なファイルと説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのメタ情報（__version__）とサブパッケージ公開

- config.py
  - 環境変数の自動ロード、settings（Settings クラス）による設定管理

- ai/
  - __init__.py
  - news_nlp.py : ニュースを銘柄ごとに集約し OpenAI でセンチメントを評価して ai_scores に保存するロジック
  - regime_detector.py : ETF (1321) の MA とマクロニュースを組み合わせて市場レジームを判定

- data/
  - __init__.py
  - jquants_client.py : J-Quants API のクライアント実装（取得・保存ユーティリティ）
  - pipeline.py : ETL パイプラインのエントリ（run_daily_etl 等）と ETLResult
  - etl.py : ETLResult の再エクスポート
  - news_collector.py : RSS 取得と raw_news 保存
  - calendar_management.py : 市場カレンダーの判定・取得・バッチ更新ロジック
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログ（signal_events / order_requests / executions）の DDL と初期化

- research/
  - __init__.py
  - factor_research.py : Momentum, Value, Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、rank、factor_summary 等

---

## テスト・開発上のヒント

- OpenAI / ネットワーク呼び出しは単体テストでモックを使うこと。コード内でも _call_openai_api を patch しやすい実装にしています。
- DuckDB はインメモリ ":memory:" を利用してテストを高速化できます（init_audit_db もサポート）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を起点）で行われます。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

---

この README は基本的な導入と主要な使い方をまとめたものです。より詳細な設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がプロジェクトにある場合は併せて参照してください。必要であれば、具体的な起動スクリプト例や CI / デプロイ手順、requirements.txt のテンプレート作成も支援します。