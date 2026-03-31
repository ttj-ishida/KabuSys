# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ集です。  
ETL（J-Quants 経由で株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（約定トレーサビリティ）、市場レジーム判定などの機能を提供します。

主な設計思想
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を中心としたデータ領域設計、ETL は冪等（ON CONFLICT）で安全に実行
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- テスト容易性を考慮したキー注入・モック差し替えポイントを提供

---

## 機能一覧

- データ取得／ETL
  - J-Quants API クライアント（株価日足・財務・上場情報・JPX カレンダー）
  - 差分 ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース周り
  - RSS 取得と前処理（news_collector.fetch_rss）
  - ニュース NLU（OpenAI を用いた銘柄別センチメント ← ai.news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成 ← ai.regime_detector.score_regime）

- 研究（Research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（research.calc_*）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー

- 監査（Audit）
  - signal_events / order_requests / executions といった監査テーブル定義・初期化（data.audit.init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを UUID 階層で保持

- ユーティリティ
  - 環境設定読み込み（config.Settings）と .env 自動ロード機構
  - 汎用統計ユーティリティ（data.stats.zscore_normalize）

---

## 必要条件（推奨）

- Python 3.10+
- 主な依存（プロジェクトに合わせて調整してください）
  - duckdb
  - openai
  - defusedxml
  - （実運用で Slack 等を使う場合は slack SDK 等を追加）

※ requirements.txt がある場合はそれに従ってください。ここに挙げたのはコード内から直接利用される主要ライブラリです。

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用される環境変数（必須は明記）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（必要な場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（必要な場合）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視ログ等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

config.Settings 経由で読み出すことができます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

環境変数が未設定で必須なものを参照すると ValueError が発生します。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 追加で Slack 等必要なパッケージをインストール
4. 環境変数を準備
   - プロジェクトルートに `.env` を作成（`.env.example` を参考に）
   - または OS 環境に直接設定
5. DuckDB データベースディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（簡易例）

以下は最小限の使い方例です。import 名や関数の引数を確認して実行してください。

- DuckDB に接続して日次 ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# ETL を当日分実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を生成:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date に対応するニュースウィンドウ（前日15:00 JST 〜 当日08:30 JST）
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 を基に）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化（別 DB を使う場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# この conn に対してオーダー監査ログを記録する操作を行う
```

- RSS フィードを取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"])
```

注意:
- ai モジュールを利用する際は `OPENAI_API_KEY` を環境変数か関数引数で渡してください。
- J-Quants の API 呼び出しには `JQUANTS_REFRESH_TOKEN` が必要です。`jquants_client.get_id_token()` がそれを用いて id_token を取得します。
- 実際の運用で約定を出す部分（broker 連携）は本リポジトリ外の実装と組み合わせる想定です。

---

## ディレクトリ構成（主なファイル）

簡易的なトップダウンツリー（src/kabusys 以下に主要モジュールがあります）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・設定ラッパー
  - ai/
    - __init__.py
    - news_nlp.py      — ニュースを銘柄別にまとめて OpenAI でスコアリング
    - regime_detector.py — マクロ＋MA200 を合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py         — ETL パイプライン（run_daily_etl など）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 収集と前処理
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - quality.py          — データ品質チェック
    - stats.py            — zscore 正規化などの統計ユーティリティ
    - audit.py            — 監査テーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py  — momentum/value/volatility のファクター計算
    - feature_exploration.py — forward returns, IC, summary, rank 等
  - ai/ (前述)
  - その他モジュール（strategy / execution / monitoring などの名前空間が package 全体で想定される）

---

## 開発上の注意点 / 実運用の注意

- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあります。コード内で空チェックを行っていますが、運用時も注意してください。
- OpenAI / J-Quants / kabu API 呼び出しはレート制御およびリトライロジックがあります。キー・ネットワークエラー時はフェイルセーフ（デフォルトスコアやスキップ）で継続する実装方針です。
- audit.init_audit_schema は transactional フラグに注意（DuckDB のトランザクション性、ネストの扱い）。
- .env のパースや自動ロードは config モジュールに実装されています。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

もし README に追加したいサンプルや、CI/デプロイ手順、具体的な schema 定義（raw_prices 等の CREATE TABLE スキーマ）などがあれば教えてください。README をそれに合わせて拡張します。