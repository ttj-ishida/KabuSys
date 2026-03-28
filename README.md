# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ（DuckDB ベース）。  
データ取得（J-Quants）、ニュース収集、AI ベースのニュースセンチメント/市場レジーム判定、ファクター計算、ETL パイプライン、監査ログ等を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等のデータを安全に取得・保存（ETL）
- RSS からニュース収集・前処理・記事→銘柄の紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）・マクロセンチメント判定
- 市場レジーム（bull/neutral/bear）判定の自動化
- 研究用のファクター計算・特徴量探索ユーティリティ
- データ品質チェック、マーケットカレンダーの管理
- 発注・約定の監査ログスキーマと初期化ユーティリティ

設計上のポイント:
- Look-ahead bias を防ぐ設計（target_date を明示、date.today()/datetime.today() に依存しない処理）
- DuckDB をメイン DB に使用
- API 呼び出しにリトライやレートリミット制御、SSRF 防御、XML の安全処理など実運用を考慮した実装
- OpenAI 呼び出しは JSON Mode を使用し、レスポンスのバリデーションを厳格化

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ保存（raw_prices / raw_financials / market_calendar へ冪等保存）

- ニュース処理
  - RSS 取得・前処理（SSRF 対策、URL 正規化、gzip 上限等）
  - raw_news / news_symbols への保存ロジック（冪等）

- AI（OpenAI）関係
  - ニュースセンチメント（score_news）: 銘柄ごとに -1.0〜1.0 を計算し ai_scores に保存
  - 市場レジーム判定（score_regime）: ETF 1321 の MA200 とマクロセンチメントを統合し market_regime に保存

- 研究 / 分析
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算（calc_forward_returns）
  - IC・統計サマリー（calc_ic / factor_summary / rank）
  - Zスコア正規化ユーティリティ（zscore_normalize）

- データ品質・カレンダー
  - 品質チェック（missing_data / spike / duplicates / date_consistency）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義
  - init_audit_db / init_audit_schema による監査 DB 初期化（UTC タイムゾーン固定）

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）、必要な環境変数参照機能（kabusys.config.settings）

---

## セットアップ

前提:
- Python 3.10 以上（| 型注釈を使用しているため）
- DuckDB を利用するため該当パッケージが必要

推奨パッケージ（例）:
- duckdb
- openai
- defusedxml

例: 仮想環境作成・インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 任意でパッケージを開発インストール
pip install -e .
```

環境変数 / .env:
プロジェクトはルート（.git または pyproject.toml があるディレクトリ）から自動で .env を読み込みます（ON）。自動読み込みを無効化するには環境変数を設定します:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主要な必須環境変数（実行に必要なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack チャネル ID
- OPENAI_API_KEY: OpenAI を使う場合に必要

システム設定:
- KABUSYS_ENV: one of "development", "paper_trading", "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下はいくつかの主要機能の呼び出し例です。実行はプロジェクトルートで行ってください。

- DuckDB 接続の作成（ファイル DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定することでルックアヘッドを防止
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントのスコアリング（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを OPENAI_API_KEY にセットしておくか、api_key=... を渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```

- 市場レジームスコアの算出（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- 監査 DB の初期化（監査ログ専用 DB を作成する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して insert / query が可能
```

注意:
- OpenAI 呼び出しは API レート・エラー・JSON 解析を考慮した実装です。テスト時は _call_openai_api をパッチしてモック可能です。
- ETL / 保存処理は DuckDB 上で冪等に動作するよう設計されています。

---

## 設定管理の挙動（.env 自動読み込み）

- 自動読み込み順序: OS 環境変数 > .env.local > .env
- プロジェクトルートは (このファイルの配置先から) 親ディレクトリを遡り、.git または pyproject.toml を基準に判定します。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

kabusys.config.settings によって設定値を参照できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル（本 README で扱ったソース群を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - etl.py (再エクスポートなど)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

※ 実際のプロジェクトには他にもモジュール（execution, monitoring, strategy 等）が存在する想定ですが、上記は今回のコードベースからの抜粋です。

---

## 運用上の注意・ベストプラクティス

- 本ライブラリは実運用（ライブ発注等）を想定した設計要素を含みます。ライブ環境に接続する前に、必ず paper_trading 環境で十分な検証を行ってください。
  - KABUSYS_ENV を "paper_trading" に設定することで挙動判定に利用できます。
- OpenAI を呼ぶ処理はコストとレートを考慮してください。ログやリトライ挙動はソース内で詳細に扱っています。
- ETL 実行時は DuckDB ファイルのパーミッションやバックアップ戦略を検討してください。
- ニュース収集や外部 URL の取り扱いは SSRF 対策等を実装していますが、運用環境のネットワークポリシーに合わせて更に制限することを推奨します。
- テストでは外部 API をモックすること（jquants_client._request、news_nlp/_call_openai_api などを patch）を推奨します。

---

## 参考・開発メモ

- OpenAI SDK の例外クラス（RateLimitError や APIError）を使った堅牢なリトライと、レスポンスの厳格な JSON バリデーションを行っています。
- DuckDB に対する executemany の挙動やバージョン差異（空パラメータの扱いなど）に配慮した実装があります（pipeline / ai/news_nlp 等）。
- ニュース記事 ID は URL 正規化後に SHA-256 を利用して生成（冪等性確保）しています。

---

必要であれば、README に次の情報を追加できます:
- 開発環境向けの requirements.txt / pyproject.toml の例
- よくあるトラブルシューティング（OpenAI エラー、DuckDB 接続エラー、J-Quants 認証失敗 など）
- 実行スクリプト例（cron ジョブ、Airflow / Dagster 用のタスク例）

追加で載せたい情報があれば教えてください。