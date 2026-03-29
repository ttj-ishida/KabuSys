# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ集合。  
DuckDB をデータストアとして用い、J-Quants / RSS / OpenAI 等と連携して以下の処理を提供します。

- データ ETL（株価、財務、マーケットカレンダー）
- ニュース収集・NLP（LLM による銘柄別センチメント算出）
- 市場レジーム判定（ETF MA とマクロニュースの融合）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、監査ログ（発注/約定のトレーサビリティ）
- （将来的に）ストラテジー / 実行 / モニタリング連携

この README はリポジトリ内の主要モジュール群（src/kabusys 以下）に基づく基本的な使い方とセットアップ手順をまとめたものです。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - ニュース収集（RSS）と前処理（SSRF/サイズ制限/トラッキング除去）
  - カレンダー管理（営業日判定、next/prev_trading_day）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に書き込み）
  - レジーム判定（score_regime: ETF 200日MA とマクロセンチメントを合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - .env / 環境変数自動読み込み、設定アクセス（settings オブジェクト）
- audit / execution / strategy / monitoring
  - 監査テーブルや実行系インフラの土台（監査テーブル DDL 等）

---

## 必要条件・依存パッケージ

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリで多くを実装）

インストール例（pip）:
```bash
pip install duckdb openai defusedxml
```

（プロジェクト用の pyproject.toml / requirements.txt があればそちらに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 依存パッケージをインストール（上記参照）
3. 環境変数を設定
   - このプロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使う場合
     - SLACK_CHANNEL_ID — Slack 通知先
     - KABU_API_PASSWORD — kabuステーション API を使う場合
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）
   - データベースパス（デフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db

例: プロジェクトルートに `.env` を置く
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 初期化（監査 DB など）

監査ログ（audit）用の DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

一般的なデータ格納用の DuckDB 接続:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

---

## 基本的な使い方（例）

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェックを含む）:
```python
from kabusys.data.pipeline import run_daily_etl
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの算出（score_news）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- z-score 正規化
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアス防止:
  - 各モジュール（news_nlp, regime_detector, pipeline 等）は内部で date 引数を受け取り、datetime.today() を直接参照しない設計です。バックテスト等で時刻を固定して再現性を保つことができます。
- OpenAI / J-Quants の API 呼び出し:
  - リトライやバックオフ、JSON 解析の堅牢化（fail-safe）を実装しています。API キーは環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）で管理してください。
- セキュリティ:
  - news_collector は SSRF・gzip bomb・大容量レスポンス対策を実装しています。RSS の URL スキームは http/https のみ許可します。
- DuckDB の互換性:
  - executemany に空リストを渡すとエラーになるバージョンを考慮し、呼び出し箇所でチェックしています。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を起点）を探索して .env, .env.local を自動読み込みします（優先順: OS 環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit.init_audit_db / init_audit_schema
  - etl などの補助モジュール
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/ (LLM 関連)
  - news_nlp.py (score_news)
  - regime_detector.py (score_regime)

（上記以外に strategy / execution / monitoring などのサブパッケージが存在する想定で記述されていますが、実行環境に応じて実装ファイルを確認してください）

---

## よくある運用フロー（例）

1. 環境変数／.env を用意する（J-Quants トークン / OpenAI Key など）
2. データベースを作成（DuckDB ファイルの配置）
3. 初回 ETL（過去データのバックフィル）
   - run_daily_etl を適切な開始日で複数日分実行して初期ロードする
4. 日次バッチ（Cron / Airflow 等）
   - 毎営業日早朝に run_daily_etl を実行
   - news_nlp.score_news と ai.regime_detector.score_regime を実行してモデルやシグナルの入力を準備
5. 監査ログ・発注:
   - audit.init_audit_db で監査用 DB を初期化
   - 発注処理は order_requests / executions テーブルに適切に書き込む（本 README は発注フローの実装例を含みません）

---

## トラブルシューティング

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。パッケージの配置場所と .git / pyproject.toml の位置を確認してください。
- OpenAI / J-Quants API 呼び出しでエラーが出る
  - 環境変数のキーが正しいか、ネットワーク・認証情報を確認してください。モジュールはリトライを実装していますが、キー無効や料金不足などは復旧しません。
- DuckDB に書き込みできない
  - ファイルパスの親ディレクトリの権限・存在を確認してください。

---

## その他

- テストや CI を導入する場合は、config の自動 .env 読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、必要な環境変数をテストスイート内で注入してください。
- 本リポジトリには実際の発注（ブローカー通信）を行う部分と組み合わせる際は、必ず「紙取引（paper_trading）」や安全フラグでまず検証してください（KABUSYS_ENV=paper_trading / live）。

---

必要であれば README にサンプル .env.example、より詳しい ETL 実行手順（初回バックフィル例）、または各モジュールの API リファレンス（関数引数や返り値の詳細）を追加できます。どちらを優先しますか？