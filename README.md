# KabuSys

バージョン: 0.1.0

KabuSysは「日本株のデータプラットフォームと自動売買のためのライブラリ群」です。J-QuantsやRSS、OpenAIなど外部データを取り込み、ETL・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログを提供します。実運用（kabuステーション連携）／リサーチ／モニタリングを想定したモジュール群で構成されています。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数一覧
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

- 日本株向けに設計されたデータ取得（J-Quants）・ETL・データ品質チェック・ニュースによるAIスコアリング・市場レジーム判定・リサーチ用ファクター計算・監査ログ等を含むライブラリ群。
- DuckDB を内部データストアとして利用し、ETLは差分取得・バックフィル・冪等保存を行う。
- ニュース解析・市場レジーム判定には OpenAI（gpt-4o-mini）を利用する構成を想定。
- Look-ahead バイアス対策や堅牢なエラーハンドリング（リトライ・フェイルセーフ）を設計方針に組み込んでいます。

---

## 主な機能

- data/
  - ETLパイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save関数、認証自動リフレッシュ、レート制御）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - RSSニュース収集（SSRF対策・トラッキングパラメータ除去・前処理）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュースNLP（score_news）：銘柄ごとのニュースセンチメントをOpenAIで評価して ai_scores に保存
  - 市場レジーム判定（score_regime）：ETF(1321)のMAとマクロニュースのLLMセンチメントを合成して market_regime に書き込み
- research/
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン / IC / 統計サマリー / ランク）
- config.py
  - 環境変数の自動読み込み（.env / .env.local の優先度、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で主要設定を取得

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈や「|」ユニオン型を使用）
- ネットワークアクセス（J-Quants、OpenAI、RSS）

1. リポジトリをクローン／配置
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクト側で requirements.txt があればそちらを利用）
4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成（以下「環境変数一覧」を参照）
   - 自動読み込みはデフォルトで有効。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. DuckDB 初期化（監査DBなど）
   - 監査ログ専用DBを初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
6. （任意）ETLの初回実行
   - DuckDB 接続を作成して run_daily_etl を呼ぶ（下の使い方参照）

---

## 環境変数一覧（必須/任意）

必須（必ず設定が必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETLで必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等で必要）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しで使用（news_nlp, regime_detector）

任意 / デフォルトあり
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env の例（プロジェクトルートに配置）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

注意:
- config.py はプロジェクトルートにある .git または pyproject.toml を基準に .env を自動検出します。テスト時などに自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単なコード例）

以下は最小限の呼び出し例です。実行前に環境変数を設定し、DuckDB パス先のディレクトリが存在することを確認してください。

1) ETL（日次パイプライン）を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースNLPで銘柄ごとにスコアを作成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY が使われる
print(f"written: {n_written} codes")
```

3) 市場レジーム判定を行う
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("done", res)
```

4) 監査DB初期化（発注/約定の保存用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を以後の監査ログ操作に利用
```

注意点:
- OpenAI の呼び出しはコストがかかります。開発・検証時は API キー管理に注意してください。
- score_news / score_regime は外部API（OpenAI）を呼び出すため、ネットワーク・レスポンス失敗に対してフェイルセーフ（0.0 スコア）や再試行ロジックがありますが、実行の可否は API キーとネットワークに依存します。
- ETL は J-Quants API を使用します。J-Quants の利用規約・レート制限に従ってください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
  - パッケージ定義。__version__ = "0.1.0"
- config.py
  - 環境変数の自動読み込み、settings オブジェクトを提供
- ai/
  - __init__.py
  - news_nlp.py: ニュースをまとめてOpenAIで評価し ai_scores に書き込む（score_news）
  - regime_detector.py: ETF 1321 の MA とマクロニュースを合成して market_regime に記録（score_regime）
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）および ETLResult
  - calendar_management.py: market_calendar 管理・営業日判定・calendar_update_job
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector.py: RSS 収集・前処理・SSRF対策
  - audit.py: 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - etl.py: pipeline.ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank
- research/* はリサーチ・バックテスト用ユーティリティ。データソースは prices_daily / raw_financials に限定しており、発注APIには触れない設計。

各モジュールは docstring で設計方針や処理フロー、フェイルセーフ動作を明示しています。関数やクラスの公開APIはモジュール内 docstring を参照してください。

---

## 運用上の注意とベストプラクティス

- 環境変数は秘匿情報です。特に OpenAI や J-Quants のトークンは安全に管理してください。
- 本リポジトリは Look-ahead バイアス対策を組み込んでいますが、バックテストやリサーチではデータ取得日時管理（fetched_at 等）に注意して運用してください。
- 本番で発注連携を行う場合は paper_trading 環境で十分に検証してから live を使用してください（KABUSYS_ENV の設定）。
- OpenAI の利用はコストに直結します。バッチサイズや呼び出し頻度に注意してください（news_nlp は銘柄ごとにチャンク処理）。

---

必要に応じて README を拡張して、セットアップスクリプト、CI／テスト手順、運用 runbook（cron化、ログ・監視連携、Slack通知の使い方など）を追加できます。何を追加したいか指定していただければ、追補します。