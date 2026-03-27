# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ（発注〜約定のトレーサビリティ）、および市場レジーム判定などを含みます。

主に DuckDB をデータ層に使い、J-Quants API や OpenAI（LLM）を外部に利用する設計です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件・依存関係
- セットアップ手順
- 環境変数（.env）一覧
- 使い方（主要 API と実行例）
- ディレクトリ構成
- 注意事項 / 運用上のヒント

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム構築のためのモジュール群です。データ取得（J-Quants）、ニュース収集と LLM を使ったセンチメント分析、ファクター計算、品質チェック、監査ログ（発注/約定トレーサビリティ）、マーケットカレンダー管理、ETL パイプラインなど、運用に必要な基盤機能を提供します。

設計上の特徴：
- DuckDB を主な永続層として使用（監査用DBは分離可能）
- Look-ahead バイアスに配慮した設計（内部で date.today() を直接参照しない等）
- 冪等性を重視（DB への保存は ON CONFLICT / UPDATE ベース）
- 外部 API 呼び出しはリトライ・バックオフやレート制御を実装
- OpenAI 呼び出しは JSON mode を想定し、レスポンス検証を行う

---

## 機能一覧

主要機能の抜粋：

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務（四半期）・上場銘柄情報・カレンダーをページネーション対応で取得
  - 差分取得・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）
  - run_daily_etl による一括 ETL 実行

- データ管理・ユーティリティ
  - DuckDB 用の保存関数（save_daily_quotes 等）
  - 統計ユーティリティ（zscore_normalize など）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）

- ニュース収集・NLP
  - RSS 取得と前処理（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - OpenAI を用いた銘柄別ニュースセンチメント（score_news）
  - マクロセンチメント + ETF MA を組み合わせた市場レジーム判定（score_regime）

- 研究用モジュール
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- 監査ログ（発注・約定トレーサビリティ）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 必要条件・依存関係

- Python 3.10+（型注釈で Union 表記などを使用）
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

実際の依存はプロジェクトの pyproject.toml / setup.py を参照してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージをインストール（編集可能インストール）
   ```bash
   pip install -e .
   # あるいは必要パッケージを個別にインストール
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` と（任意で）`.env.local` を配置すると、自動で読み込まれます。
   - 自動ロードは、プロジェクトルートが `.git` または `pyproject.toml` によって検出される場合に実行されます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB ファイル準備
   - デフォルトでは data/kabusys.duckdb に接続する設計です（設定は環境変数で変更可）。

---

## 環境変数（主要なもの）

アプリケーションは環境変数から設定を読み取ります。必須のものとデフォルトを示します。

必須（未設定だと例外になる）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API パスワード（発注等で利用）
- SLACK_BOT_TOKEN : Slack 通知用 bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV : 実行環境。allowed: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL） デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロード無効化（1 を設定）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用可能）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL : kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）

`.env` 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: config モジュールはクォートやコメント付きの .env フォーマットをかなり丁寧にパースします（export 形式やクォートエスケープもサポート）。

---

## 使い方（主要 API と実行例）

以下はライブラリを Python インタプリタやスクリプトから使う際の代表的な例です。各関数は DuckDB の接続オブジェクトを受け取ります（例: duckdb.connect(...)）。

1) DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行します。
- ETLResult に保存結果や品質問題、エラーメッセージが格納されます。

3) ニューススコア生成（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
# api_key を None にすると環境変数 OPENAI_API_KEY を参照します
print("scored codes:", n_written)
```
- 前日 15:00 JST ～ 当日 08:30 JST を対象にニュースを集約し銘柄ごとの ai_score を ai_scores テーブルへ書き込みます。
- OpenAI API 呼び出しにはリトライ・バックオフ、レスポンスの厳格バリデーションを行います。
- テスト容易性のため _call_openai_api は差し替え（mock）可能です。

4) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
# 市場レジーム（bull/neutral/bear）を market_regime テーブルに書き込みます
```
- ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して判定します。

5) 監査ログ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は親ディレクトリを自動作成し、スキーマを transactional に作成します
```

6) マーケットカレンダー関数
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

7) J-Quants から手動でデータを取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## テスト / モックについて

- OpenAI 呼び出しは内部で _call_openai_api を使用しています。テストでは unittest.mock.patch で差し替え可能です（score_news / regime_detector 各モジュール内の _call_openai_api をモック）。
- news_collector の HTTP 層（_urlopen 等）も差し替え可能に設計されています。

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV が `live` の場合は実際の発注やマネタリーリスクが伴うため、運用時のアクセス権限やログ設定・監視体制に留意してください。
- OpenAI や J-Quants の API コールは料金・レート制限があるため、本番運用では適切なキャッシュ・レート制御を行ってください（jquants_client は固定間隔スロットリングを実装済み）。
- DuckDB の executemany はバージョン依存の挙動があるため、モジュール内で空リストバインドを避ける実装があります。ライブラリを直接改変する場合はその点に注意してください。
- news_collector は SSRF 対策・最大レスポンスサイズチェック・gzip 解凍後のサイズチェックなどセキュリティ対策を実装しています。RSS ソースを追加する際は信頼できるソースを使ってください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                         — 環境変数/設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                      — 銘柄別ニュースセンチメント（score_news）
  - regime_detector.py               — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py           — 市場カレンダー管理、calendar_update_job
  - etl.py / pipeline.py             — ETL パイプライン / ETLResult
  - jquants_client.py                — J-Quants API クライアント & 保存関数
  - news_collector.py                — RSS 収集・前処理
  - quality.py                       — データ品質チェック
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - audit.py                         — 監査ログテーブル DDL / init_audit_db
  - etl.py                           — ETL インターフェース再エクスポート
- research/
  - __init__.py
  - factor_research.py               — momentum / value / volatility
  - feature_exploration.py           — calc_forward_returns / calc_ic / factor_summary / rank

その他、strategy / execution / monitoring 用のパッケージ名が __all__ に含まれており、将来的に戦略ロジックや約定実装を配置する想定です。

---

以上が README の概要です。必要であれば、
- インストール可能な requirements.txt / pyproject.toml のテンプレート
- 具体的な .env.example ファイル（全設定のテンプレート）
- より詳細な API リファレンス（各関数の引数・戻り値一覧）
を追加で生成します。どれが必要か教えてください。