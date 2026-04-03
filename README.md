# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの市場データ取り込み）、ニュース収集・NLP による銘柄スコアリング、ファクター算出、研究用ユーティリティ、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

このプロジェクトは以下の関心事を分離して実装しています。

- データ取得（J-Quants API）と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF 1321 の MA + マクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用解析（IC, forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

設計上の特徴：
- DuckDB を中心に SQL と最小限の Python ロジックで実装
- Look-ahead bias 防止を考慮した時刻/日付処理
- API 呼び出しに対するリトライ・レート制御・フェイルセーフ設計
- セキュリティ対策（RSS の SSRF ブロック、defusedxml の利用など）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から daily quotes / financial statements / market calendar 等の取得
  - DuckDB への save_* 関数（冪等保存）
  - トークン取得 & キャッシュ、レートリミット制御、リトライ
- data.pipeline / etl
  - 日次差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を ETLResult として集約
- data.news_collector
  - RSS 取得、記事正規化、記事ID生成、raw_news への保存（冪等）
  - SSRF 対策・受信サイズ制限
- ai.news_nlp
  - 銘柄ごとにニュースを集約し OpenAI へ投げて ai_scores に保存（score_news）
- ai.regime_detector
  - ETF 1321 の 200 日移動平均乖離とマクロセンチメントを合成して market_regime に保存（score_regime）
- research.*
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- data.audit
  - 監査用テーブル群の初期化・スキーマ（init_audit_schema / init_audit_db）
- config
  - .env / .env.local / OS 環境変数の読み込みロジック（自動ロード可否フラグあり）
  - settings オブジェクト経由で各種設定へアクセス

---

## セットアップ手順

以下はローカル環境で開発・実行するための基本手順です。

1. Python（3.10 以上推奨）を用意する。

2. 必要パッケージをインストール（例）:
   - duckdb
   - openai
   - defusedxml
   - （その他、プロジェクトで使用するパッケージ）
   
   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定する:
   - 推奨はプロジェクトルートに `.env`（および開発時に `.env.local`）を置く方法です。
   - 自動ロードは `kabusys.config` により行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（実行する機能に応じて設定が必要）:
   - JQUANTS_REFRESH_TOKEN=...    # J-Quants の refresh token（ETL）
   - OPENAI_API_KEY=...          # OpenAI API キー（ニュース NLP / レジーム判定）
   - KABU_API_PASSWORD=...       # kabu ステーション API パスワード（発注を使う場合）
   
   任意:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
   - LOG_LEVEL=DEBUG|INFO|...  (デフォルト INFO)
   - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
   - SQLITE_PATH=data/monitoring.db
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知に使用する場合）

   例 `.env`（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データディレクトリの準備（必要なら）:
   - デフォルトでは `data/` 配下に DB 等を作成します。存在しない場合は自動作成される実装の箇所もありますが、必要に応じて `mkdir -p data` を行ってください。

---

## 使い方（簡単なコード例）

以下は代表的な呼び出し例です。いずれも Python スクリプト中から呼び出せます。

- DuckDB 接続を作る（設定で指定されたパスを利用）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env から OPENAI_API_KEY を取得
print(f"written scores: {written}")
```

- 市場レジームを算出して market_regime に書き込む:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用：ファクター計算 / forward returns:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns

date0 = date(2026,3,20)
mom = calc_momentum(conn, date0)
fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
```

- 監査 DB を初期化（別 DB を使う場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

注意点（運用上の指針）:
- OpenAI 呼び出しや外部 API 呼び出しはコストやレート制限があります。適切にキーを管理し、想定外の大量呼び出しを避けてください。
- ETL / AI スコアリングは Look-ahead bias を避ける設計になっています（target_date 未満のデータのみを使用する等）。

---

## 主要ディレクトリ構成

（src/kabusys 以下の主要モジュールと簡単な説明）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み (.env/.env.local) と settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを計算して ai_scores に保存
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): マクロ + ETF MA で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / get_id_token 等）
    - pipeline.py
      - ETL 実行の中心（run_daily_etl, run_prices_etl, ...）
      - ETLResult データクラス
    - etl.py
      - ETLResult の再エクスポートインターフェース
    - news_collector.py
      - RSS 収集・前処理・保存（SSRF対策、トラッキング除去）
    - calendar_management.py
      - market_calendar の管理と営業日判定ユーティリティ
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
    - audit.py
      - 監査ログテーブル定義、初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

---

## 環境変数 / .env の挙動

- 読み込み順:
  1. OS 環境変数（最優先）
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば読み込み）
- 自動ロードを無効にするには:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- Settings で未定義の必須変数を参照した場合は ValueError を送出します（例: JQUANTS_REFRESH_TOKEN が未設定で get_id_token を呼ぶ等）。

---

## 注意事項 / 運用上のポイント

- OpenAI（gpt-4o-mini）利用時は API レートとコストに注意してください。失敗時はフェイルセーフとして 0.0 スコアにフォールバックする実装が多く入っています。
- J-Quants API へのアクセスはレート制御（120 req/min）やリトライ、401 時の自動リフレッシュを備えています。
- RSS 取り込みでは SSRF 対策（リダイレクト検査、プライベート IP の除外）、受信サイズ制限を行っていますが、実運用ではさらに堅牢なプロキシ設定等を検討してください。
- DuckDB のバージョン差による挙動差（executemany の空リスト取り扱い等）を考慮した実装になっていますが、使用する DuckDB のバージョンを固定することを推奨します。

---

README に記載の以外でサンプル・運用スクリプトや schema 初期化スクリプト等が必要な場合は、その用途に合わせたテンプレートを提供できます。必要な出力形式（例: 英語版 README、簡易 Quickstart スクリプト等）があればお知らせください。