# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants 経由の株価 / 財務 / カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

パッケージバージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイルおよび環境変数の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で設定値取得

- データ ETL（J-Quants API）
  - 株価日足（OHLCV）の差分取得・保存（ページネーション対応、レートリミット・リトライ）
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（run_daily_etl）

- ニュース関連
  - RSS フィード収集（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - ニュース → 銘柄マッピング、raw_news 保存
  - OpenAI を使ったニュースセンチメント解析（batch、JSON-mode、リトライロジック）
  - ai_scores テーブルへの書き込み（score_news）

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損データ、主キー重複、スパイク（前日比）・日付整合性チェック（run_all_checks）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化・DB作成（冪等・UTCタイムスタンプ）
  - init_audit_db / init_audit_schema による初期化ユーティリティ

---

## 前提（必須 / 推奨依存）

最低限必要な Python パッケージ（代表的なもの）:
- duckdb
- openai
- defusedxml

例（pip）:
pip install duckdb openai defusedxml

※ 他に logging 等標準ライブラリ以外の追加依存がある場合はプロジェクトの requirements を参照してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt  または
   - pip install duckdb openai defusedxml

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須となる主要な環境変数（本番や特定機能を使う場合）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注周り）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
※ 環境変数は settings オブジェクト（kabusys.config.settings）から取得されます。

.env の自動読み込み順序:
- OS 環境変数 > .env.local > .env
（ただし、プロジェクトルートが特定できない場合は自動読み込みはスキップされます）

4. DuckDB ファイル等の保存先（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb（settings.duckdb_path）
- SQLITE_PATH: data/monitoring.db（settings.sqlite_path）
これらは環境変数で上書きできます。

---

## 使い方（代表的な例）

下記は Python から利用する簡単な例です。各関数は duckdb の接続オブジェクトを受け取ります。

- 共通インポート例
```python
import duckdb
from datetime import date
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（score_news）
```python
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("完了" if res == 1 else "失敗")
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は初期化済みの duckdb 接続
```

- 研究モジュールの利用（例：モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
# moms は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- すべての関数はルックアヘッドバイアス回避のため、内部で date.today() 等に依存しない設計になっています（target_date を明示してください）。
- OpenAI 呼び出しは独自のリトライや JSON-mode を利用しており、API失敗時はフェイルセーフとして 0.0 を返すなどの挙動があります（ログを参照）。

---

## 開発・デバッグ時のヒント

- .env の自動読込を無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- テストやモック:
  - OpenAI 呼び出し部（news_nlp._call_openai_api / regime_detector._call_openai_api）はテスト時に patch して差し替え可能です。

- ログレベル:
  - LOG_LEVEL 環境変数（DEBUG / INFO / …）で制御できます。settings.log_level を通じて取得されます。

---

## ディレクトリ構成（抜粋）

プロジェクトは `src/kabusys` 配下に実装されています。主要ファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py                       — パッケージ初期化（__version__）
  - config.py                         — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py                     — AI 関連エクスポート
    - news_nlp.py                     — ニュースセンチメント解析（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py          — マーケットカレンダー管理（is_trading_day 等）
    - etl.py                          — ETL の公開インターフェース（ETLResult）
    - pipeline.py                     — ETL パイプラインと個別 ETL（run_daily_etl など）
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログテーブル定義 / 初期化
    - jquants_client.py               — J-Quants API クライアント（取得 + 保存）
    - news_collector.py               — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py              — ファクター計算（momentum, value, volatility）
    - feature_exploration.py          — 将来リターン・IC・統計サマリー
  - research/...（その他研究ヘルパ）
  - (その他: strategy, execution, monitoring 等の名前空間が __all__ に含まれる想定)

各モジュールはドキュメント文字列やログ出力を意図的に実装しており、設計方針（ルックアヘッド回避、フェイルセーフ、冪等性など）が各所に記載されています。

---

## 補足

- 本リポジトリはデータ取得（ETL）・前処理・解析・監査ログまでを提供する基盤ライブラリです。発注周り（実際のブローカー連携）や Slack 通知などの実装は別モジュール／上位アプリケーション側で行う想定です（ただし設定項目は用意されています）。
- OpenAI / J-Quants API の利用はそれぞれのサービス契約に従ってください。API キーやトークンは安全に管理してください。

---

必要であれば README に「例となる .env.example」や「requirements.txt の推奨内容」「簡単なユニットテストの実行方法」などを追加できます。どの情報を追記しますか？