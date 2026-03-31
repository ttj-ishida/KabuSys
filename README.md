# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、量的運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成された Python パッケージです。

- データ収集（J-Quants API 経由）および DuckDB への保存（冪等）
- 日次 ETL パイプライン（株価・財務・市場カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集と前処理
- ニュースに対する LLM ベースのセンチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF MA と LLM マクロセンチメントの合成）
- リサーチ用のファクター計算 / 特徴量解析ユーティリティ
- 取引監査ログ（信号→発注→約定のトレーサビリティ）を保持する監査 DB 初期化

設計方針の主なポイント:
- Look-ahead bias を避けるため、内部で date.today()/datetime.today() を無暗に参照しない実装
- API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- DuckDB を用いたローカルデータレイヤー（冪等保存/トランザクション考慮）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から株価 / 財務 / カレンダーを取得し DuckDB に保存する
  - レートリミット・指数バックオフ・トークン自動リフレッシュ対応
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェックの一括処理
- data.news_collector
  - RSS 取得、URL 正規化、記事 ID 生成、raw_news への冪等保存
  - SSRF / gzip bomb 等の防御処理を実装
- ai.news_nlp
  - LLM（gpt-4o-mini）を使った銘柄ごとのニュースセンチメントスコア生成（score_news）
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアを合成して market_regime を算出（score_regime）
- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化
- data.quality
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- data.audit
  - 取引監査用テーブル群の DDL と初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 必要環境 / 依存

- Python 3.10+
- パッケージ（主なもの）
  - duckdb
  - openai（OpenAI の Python SDK）
  - defusedxml
- その他標準ライブラリ（urllib, json, logging など）

（実際の requirements.txt／pyproject.toml を用意してください。ここでは実装上必要な主要パッケージを挙げています。）

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを配置

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存インストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して `pip install -r requirements.txt` または `pip install .` を推奨します。

4. 環境変数（.env）を用意
   - プロジェクトルートの `.env` / `.env.local` を自動でロードします（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_station_api_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C...
   - OPENAI_API_KEY=sk-...
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   .env のサンプル（README 用）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（主要な API 使用例）

以下は基本的な利用例です。実行はプロジェクトルートで行い、環境変数が正しく設定されていることを確認してください。

- DuckDB 接続を作る（設定のパスを利用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（全処理：カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP スコアを生成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# API キーを引数で渡すか、環境変数 OPENAI_API_KEY を使う
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- 市場レジーム（market_regime）を算出する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル群が作成されます
```

- 研究用：ファクター計算、将来リターン、IC 計算
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
fwd = calc_forward_returns(conn, target_date=date(2026, 3, 20))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

注意点:
- OpenAI を使う関数は API キーを環境変数（OPENAI_API_KEY）または関数引数で与えてください。
- ETL / API 呼び出しはネットワーク IO やリトライを伴います。ログを確認しながら利用してください。
- DuckDB のバージョンや環境により executemany の挙動が異なるため、既定の保存関数は空パラメータに対する安全策を実装しています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で利用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等で使用）パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env の自動ロードを無効化

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- __init__.py
  - パッケージ初期化、バージョン情報

- config.py
  - 環境変数読み込み・管理（.env 自動ロード、設定プロパティ）

- ai/
  - news_nlp.py : ニュースの LLM センチメント付与（score_news）
  - regime_detector.py : ETF MA とマクロセンチメントを合成した市場レジーム判定（score_regime）
  - __init__.py

- data/
  - jquants_client.py : J-Quants API クライアント（取得・保存）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）および ETLResult
  - news_collector.py : RSS 収集・前処理
  - calendar_management.py : 市場カレンダー管理・営業日ロジック
  - quality.py : データ品質チェック（各種チェック関数）
  - stats.py : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py : 監査ログスキーマの定義・初期化
  - etl.py : ETLResult の再エクスポート
  - __init__.py

- research/
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン、IC、統計サマリー等
  - __init__.py

---

## ロギング / トラブルシューティング

- LOG_LEVEL 環境変数でログレベルを調整してください（デフォルト INFO）。
- API 呼び出し（OpenAI / J-Quants）はネットワークやレート制限に依存します。警告や例外メッセージを参照してください。
- 自動で .env を読み込む処理は config.py 内で行われます。テスト時などに無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発メモ / テストフック

- ai モジュール内の OpenAI 呼び出しは内部のラッパー関数（_call_openai_api）を通しており、単体テストではパッチして差し替えられる設計です。
- news_collector はネットワークアクセス／SSRF 検査を強化しています。外部接続をモックしてテストしてください。
- DuckDB に対する executemany の空リスト扱い等、実行環境の DuckDB バージョンによる挙動に注意しています。

---

この README は実装をベースにした概要と基本的な使い方をまとめたものです。詳細な API 引数・戻り値や運用設定はコード内の docstring を参照してください。必要であれば README を拡張して実運用向けの手順（cron や Airflow 連携、Slack 通知設定、kabuステーションとの接続方法など）を追加できます。