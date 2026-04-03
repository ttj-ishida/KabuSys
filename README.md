# KabuSys

日本株向けの自動売買／リサーチプラットフォームのコアライブラリです。  
このリポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどトレーディング／リサーチに必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ETL）
- DuckDB を利用した時系列データの格納・集計処理
- ニュース記事の収集・前処理、OpenAI によるセンチメント評価（銘柄別 ai_score）
- ETF（1321）の MA とマクロニュースを組み合わせた市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算／探索用ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマの初期化と運用支援
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計で重視している点：
- ルックアヘッドバイアスを避ける（内部で datetime.today() 等に依存しない設計）
- 冪等性（ETL／保存処理は idempotent）
- フェイルセーフ（API 失敗時は継続、致命的な停止を避ける）
- 外部サービス呼び出しは明示的に API キーを受け取る／環境変数から取得する

---

## 機能一覧（概要）

- kabusys.config
  - 環境変数の読み込み（プロジェクトルートの `.env` / `.env.local` を自動ロード）
  - settings オブジェクトによりアプリ設定を取得
- kabusys.data
  - jquants_client: J-Quants API ラッパー（取得／保存／認証／レート制御、DuckDB 保存関数）
  - pipeline: 日次 ETL パイプライン（run_daily_etl）と ETLResult
  - news_collector: RSS 取得→正規化→raw_news 保存（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック群（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別に集約し OpenAI でセンチメント評価、ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュース LLM スコアを合成して market_regime を書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ（開発環境）

前提
- Python 3.10+（typing の `X | Y` を使用）
- duckdb, openai, defusedxml 等の依存あり

手順（例）:

1. リポジトリをクローンして仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   ※requirements.txt は本例では省略。最低限は以下をインストールしてください。
   ```
   pip install duckdb openai defusedxml
   ```
   （追加のロギング・テスト用パッケージ等は必要に応じて）

3. 開発インストール（パッケージとして使いたい場合）
   ```
   pip install -e .
   ```
   （setup.py / pyproject.toml がある前提）

4. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を置くか、OS 環境変数で設定します。`kabusys.config` はプロジェクトルート（.git または pyproject.toml のある親）から自動で `.env` ロードを試みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
   - SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
   - KABUSYS_ENV: `development` / `paper_trading` / `live`
   - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

   .env ファイルはシェル風の記法をサポートします（export プレフィックス、クォート、コメント等）。詳細なパースは kabusys.config の実装に従います。

---

## 使い方（主要ユースケース）

以下は簡単な利用例です。実運用ではエラーハンドリングやロギング設定を適切に行ってください。

1) DuckDB 接続の作成（設定からパスを取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```
- run_daily_etl はカレンダー→株価→財務→品質チェックを順に実行し ETLResult を返します。

3) ニュースセンチメントのスコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 必要に応じて api_key を直接渡すことも可能（None の場合は OPENAI_API_KEY 環境変数を使用）
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"written {n_written} ai_scores")
```

4) 市場レジームのスコアリング
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```
- 内部で OpenAI（gpt-4o-mini）を呼び出します。OpenAI API の失敗はフェイルセーフで macro_sentiment = 0.0 にフォールバックします。

5) 監査ログスキーマ初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

6) ファクター計算・研究用関数（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum_records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 環境変数自動ロードの挙動（重要）

- デフォルトでパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を検出）から `.env`（優先度低）および `.env.local`（優先度高）を自動で読み込みます。
- OS 環境変数が既に設定されているキーは `.env` で上書きされません。`.env.local` は override=True のため OS 環境変数以外は上書きされます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで使用）。

---

## ディレクトリ構成

主要なファイル／パッケージ（src/kabusys 配下）:

- kabusys/
  - __init__.py                             - パッケージ初期化（version 等）
  - config.py                               - 環境設定・.env ロード
  - ai/
    - __init__.py
    - news_nlp.py                            - ニュース NLP（score_news、calc_news_window 等）
    - regime_detector.py                     - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                      - J-Quants API クライアント（取得／保存）
    - pipeline.py                            - ETL パイプライン（run_daily_etl 等）
    - etl.py                                 - ETLResult 再エクスポート
    - news_collector.py                       - RSS 収集・正規化・保存
    - calendar_management.py                 - マーケットカレンダー管理（is_trading_day など）
    - quality.py                             - データ品質チェック（QualityIssue）
    - stats.py                               - zscore_normalize 等
    - audit.py                               - 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py                     - 各ファクター計算（momentum/value/volatility）
    - feature_exploration.py                 - 将来リターン・IC・統計サマリー等

この README はコードベースの主要モジュールと役割を簡潔にまとめたものです。各モジュールの詳細（パラメータ仕様、戻り値、例外動作など）はソース内の docstring を参照してください。

---

## 注意点 / 運用上のヒント

- OpenAI API の呼び出しには料金が発生します。news_nlp / regime_detector はバッチ呼び出し・リトライ・バッチサイズ制御をしていますが、利用前にコストを確認してください。
- J-Quants の API レート制限（120 req/min）に合わせた RateLimiter 実装があります。get_id_token（トークンリフレッシュ）などの扱いに注意してください。
- DuckDB に対する executemany の空パラメータはバージョン差で問題になるため、コード中で空チェックを行っています。運用環境の DuckDB バージョンに留意してください。
- 監査ログは削除しない前提です。スキーマ・容量設計は運用方針に合わせて検討してください。
- テスト時は kabusys.ai モジュール内の API 呼び出しをモックすることを推奨します（ソース内に差し替えポイントを用意しています）。

---

もし README に追記して欲しいサンプルや、CI 用セットアップ手順、あるいは具体的な .env.example の内容（必須キー一覧など）が必要であれば教えてください。