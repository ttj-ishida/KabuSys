# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や RSS、OpenAI（LLM）等の外部データと連携して、データ収集（ETL）、品質チェック、ニュース NLP、ファクター計算、監査ログ（注文トレーサビリティ）などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュースの収集（RSS）と LLM による銘柄単位センチメント評価（ai_scores）
- マクロニュースと ETF（1321）の移動平均乖離を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ付き）

設計方針として、ルックアヘッドバイアスを避ける・冪等性を重視する・外部リソースの障害に対してフェイルセーフを持たせることを重視しています。

---

## 主な機能（抜粋）

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API とのページング対応・レート制限対応・トークン自動リフレッシュ（kabusys.data.jquants_client）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、将来日付、非営業日データの検出
- ニュース収集 / 前処理（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、記事 ID 生成、raw_news への冪等保存想定
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini による銘柄単位センチメント評価（バッチ・リトライ・レスポンス検証）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM スコアの合成
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / バリュ / ボラティリティ計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル用 DDL / 初期化関数

---

## セットアップ手順

必要条件
- Python 3.10 以上（typing の | 演算子を利用しているため）
- ネットワークアクセス（J-Quants / OpenAI 等）

推奨パッケージ（参考）
- duckdb
- openai (OpenAI SDK)
- defusedxml

インストール（ローカル開発）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. ビルド / インストール
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"     # setup.py/pyproject がある前提で editable install
# 依存パッケージを明示的に入れる場合:
pip install duckdb openai defusedxml
```

環境変数
- プロジェクトルートに `.env` / `.env.local` があると自動でロードされます（kabusys.config の実装）。
  - 自動ロードを一時的に無効にする場合:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants の refresh token）
  - KABU_API_PASSWORD（kabuステーション API 用のパスワード）
- LLM を使う機能では OPENAI_API_KEY を使用します（関数呼び出しで引数として渡すことも可能）。

（以降の「環境変数 / 設定」節に詳細を記載します）

---

## 使い方（簡単な例）

以下は主要なユースケースの最小例です。実行前に必要な環境変数（上記参照）を設定してください。

1) DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J-Quants トークンを環境経由または id_token 引数で渡す）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメント（ai_scores）を作成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {written}")
```

4) 市場レジームをスコアリングして market_regime テーブルへ書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用 DB の初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/monitoring_audit.duckdb")
# 以後、order / executions を記録するためにこの接続を使用
```

6) 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

ログ
- LOG_LEVEL は環境変数で制御できます（デフォルト INFO）。kabusys.config の Settings.log_level を参照してください。

---

## 環境変数 / 設定一覧（主なもの）

kabusys.config.Settings によって環境変数をラップしています。主なキーは以下。

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)

- OpenAI / LLM
  - OPENAI_API_KEY (関数呼び出し引数でも可能)
  - PAPER_FILL_MODE (paper trading mock fill mode: instant|partial|never|reject, default "instant")

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- データベース / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)

- 監視 / 実行設定
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

- 実行環境フラグ
  - KABUSYS_ENV (development | paper_trading | live) — Settings.is_live / is_paper / is_dev を影響
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env の例（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env ロード
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を順に読み込みます。
- OS 環境変数が優先されます。.env.local は上書きフラグ（override）で優先して適用されます。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト利用等）。

---

## ディレクトリ構成（主要ファイル）

パッケージは src/kabusys 以下に配置されています。主要モジュール：

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（銘柄単位）
    - regime_detector.py      — マクロ + ETF による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS ニュース収集（正規化・SSRF 対策）
    - calendar_management.py  — 市場カレンダーの判定・更新ロジック
    - audit.py                — 監査ログスキーマ初期化
    - etl.py                  — ETLResult 再エクスポート
    - stats.py                — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility ファクター
    - feature_exploration.py  — forward returns / IC / summary / rank

ドキュメントや設計メモは各モジュール冒頭の docstring に詳述されています。実装上の多くの設計判断（ルックアヘッドバイアス対策、冪等性、リトライ戦略、ロギング方針等）もコード中のコメントに記載されています。

---

## 注意事項 / 運用上のヒント

- OpenAI 呼び出しはコストがかかります。バッチサイズやモデルの選定を慎重に行ってください（デフォルトは gpt-4o-mini）。
- J-Quants API のレート制御は jquants_client に実装されていますが、運用時は API 利用制限に注意してください。
- DuckDB のバージョン差異により executemany の挙動が異なる場合があるため、pipeline 等では空のパラメータでの executemany を避ける工夫がされています。
- ニュース収集は SSRF 対策（リダイレクトチェック・プライベートIP除外等）や XML パースの保護（defusedxml）を実装していますが、運用環境での追加対策や監視は推奨します。

---

必要であれば README にサンプル .env.example、CI/テスト実行方法、より細かな API リファレンス（各関数の引数/戻り値の表）を追加できます。どの情報を優先して追記するか指示してください。