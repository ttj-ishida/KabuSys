# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。  
データ ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI を利用したセンチメント）、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）、およびマーケットカレンダー管理などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python モジュール群です。主な責務は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務データ、上場銘柄情報、JPX カレンダー）
- DuckDB を用いた差分 ETL パイプライン（保存・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策など安全設計）
- OpenAI（gpt-4o-mini等）を用いたニュースセンチメント分析・市場レジーム判定
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査用テーブル（signal → order_request → execution）の初期化・管理
- 各種ユーティリティ（マーケットカレンダー判定、統計正規化、データ品質チェック）

設計上の特徴：
- ルックアヘッドバイアスを避ける（内部で date.today() をブラックボックスで参照しない設計）
- 冪等性（ON CONFLICT / idempotent 保存）を重視
- API 呼び出しはリトライ / バックオフ / レート制御を実装
- セキュリティ配慮（RSS の SSRF 対策、XML の安全パース等）

---

## 機能一覧（抜粋）

- data.jquants_client: J-Quants API クライアント（取得・保存・ページネーション・認証リフレッシュ）
- data.pipeline: 日次 ETL（差分取得、保存、品質チェック）
- data.calendar_management: 市場カレンダー管理と営業日ロジック
- data.news_collector: RSS 収集・前処理・raw_news 保存補助（SSRF・gzip・トラッキング除去など）
- data.quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
- data.audit: 監査ログ用スキーマ初期化（signal_events / order_requests / executions）
- ai.news_nlp: ニュースを銘柄別にまとめて LLM でスコアリング（JSON Mode + バッチ）
- ai.regime_detector: ETF(1321) の MA200 とニュースセンチメントを合成した市場レジーム判定
- research: ファクター計算／特徴量探索（モメンタム・ボラティリティ・バリュー・IC 等）
- data.stats: z-score 正規化などの統計ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `X | None` を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

推奨手順（UNIX 系の例）:

1. 仮想環境の作成・有効化
```bash
python -m venv .venv
source .venv/bin/activate
```

2. 必要パッケージのインストール（代表的パッケージ）
（実プロジェクトでは requirements.txt を用意して管理してください）
```bash
pip install duckdb openai defusedxml
```

3. 開発インストール（ソース直下で）
```bash
pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（実行モジュールで使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルト DuckDB パス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

自動 .env ロード:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動ロードします。
- 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例: .env
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表例）

※ 以下は簡単な利用例です。 DuckDB 上のテーブルスキーマは本リポジトリの外部スクリプトで整備されることを想定しています（特に raw_prices/raw_financials/raw_news/ai_scores/market_calendar 等）。audit 用の初期化はライブラリで提供しています。

1) DuckDB 接続の準備（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュースの AI スコアリング（前日15:00 JST ～ 当日08:30 JST のウィンドウを対象）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査 DB（監査用テーブル）の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルおよび索引が作成されます
```

6) 研究用関数の利用例（モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum_records = calc_momentum(conn, date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

7) マーケットカレンダー関数例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
if is_trading_day(conn, d):
    nxt = next_trading_day(conn, d)
```

注意点：
- OpenAI 呼び出し時は API のエラーに対して内部的にリトライやフォールバック（失敗時はスコア 0.0）を行いますが、API キーが未設定だと ValueError を送出します。
- news_collector は RSS の安全な取り込み（SSRF ブロック、gzip サイズ制限、XML の安全パース）を実装しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、バッチ処理、バリデーション）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理・営業日判定
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（z-score）
  - audit.py — 監査ログスキーマの作成・初期化
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ、ランク関数
- research/*（その他） — 追加のリサーチユーティリティ
- （その他）strategy, execution, monitoring モジュール群（パッケージ公開対象）

---

## 運用上の注意 / ベストプラクティス

- 本コードベースでは Look-ahead bias 回避を重視しています。バックテストやバッチ実行時は target_date を明示的に渡す等、意図しない現在時刻参照が入らないよう注意してください。
- DuckDB のスキーマ（raw_prices / raw_financials / raw_news / market_calendar / ai_scores 等）は ETL を動かす前に準備しておく必要があります（スキーマ定義は別スクリプトやドキュメントで提供してください）。audit.init_audit_db は監査用スキーマを自動作成します。
- 環境変数は .env/.env.local で管理できます。`.env.local` は `.env` を上書きします（OS 環境変数はさらに優先されます）。
- OpenAI / J-Quants の API 呼び出しにはそれぞれコスト・レート制限があるため、実運用ではキー管理と呼び出し間隔に注意してください。
- ニュース収集や外部 API 呼び出しのテストは外部依存を切り離すためモック可能な実装（内部関数の差し替え）を行っています。ユニットテスト時は適切に patch してください。

---

README はここまでです。より詳細な設定例、DB スキーマ、運用手順（cron/ジョブスケジューリング、監視アラート設定等）や、strategy/execution 部分の使用方法について追加ドキュメントが必要であれば教えてください。