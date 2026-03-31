# KabuSys

日本株向け自動売買 / データプラットフォーム用 Python ライブラリセットです。  
市場データの ETL、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、およびレジーム判定等のユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ収集・品質管理・AI スコアリング・リサーチ・監査テーブル構築までをカバーするモジュール群です。主な目的は以下です。

- J-Quants API からのデータ ETL（株価・財務・取引カレンダー等）
- RSS ベースのニュース収集と OpenAI を用いたセンチメント算出（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA とマクロニュースの組合せ）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → executions）用のスキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴として、ルックアヘッドバイアス対策（日時の明示的取り扱い）、外部 API の堅牢なリトライ/フェイルセーフ、DuckDB ベースのローカル保存、OpenAI の JSON Mode 利用などが盛り込まれています。

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出、.env/.env.local 優先順位）
  - 必須設定取得ユーティリティ（settings オブジェクト）

- データ収集・ETL（kabusys.data）
  - J-Quants クライアント（レート制限管理・トークンリフレッシュ・ページネーション）
  - daily quotes / financial statements / market calendar の取得と DuckDB への冪等保存
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ニュース収集（RSS）と raw_news 保存（SSRF 対策・トラッキング除去）
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- AI 関連（kabusys.ai）
  - ニュース NLP による銘柄別センチメントスコアリング（score_news）
  - マクロニュース + ETF MA による市場レジーム判定（score_regime）

- リサーチ（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
  - 統計ユーティリティ: zscore_normalize

- その他ユーティリティ
  - 統計関数（z-score 正規化）
  - DB 初期化サポート、監査用インデックス定義等

---

## セットアップ手順

前提:
- Python 3.9+（typing の Union 省略表記などに依存）
- DuckDB を利用するためネイティブパッケージが必要（pip で duckdb をインストール可能）

1. ソースを取得
   - レポジトリをクローンまたはパッケージを展開してください。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合は少なくとも以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml
     - （必要に応じて）その他のネットワーク関連やロギング用ライブラリ

   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を置くことで自動ロードされます。
   - 自動ロードを無効にする場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時は http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API を使う機能（score_news / score_regime）で使用（関数に api_key を渡すことも可能）
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: 開発/ペーパー/本番 ("development" / "paper_trading" / "live")
   - LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")

5. データベース初期化（監査ログ）
   - 監査用スキーマを別 DB に作成する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - または既存の DuckDB 接続に対してスキーマを適用:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要なユースケース）

以下は代表的な呼び出し例です。実行は Python スクリプトまたは REPL で行えます。

- settings を使った設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- 日次 ETL 実行（run_daily_etl）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))  # settings は上で import 済み
result = run_daily_etl(conn, target_date=None)   # target_date を省略すると今日
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（上記セットアップ参照）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算の呼び出し例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

注意点:
- OpenAI 呼び出しには API キーが必要です（api_key 引数で注入可能）。API 呼出しはリトライやエラー時のフォールバック設計が組み込まれていますが、レート制限・料金に注意してください。
- ETL / AI 機能は実ネットワークを使うため、テスト時は該当関数の HTTP 呼び出し部分をモックすることを推奨します（コード内でモックしやすい設計になっています）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールとその役割です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings オブジェクト（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースの OpenAI による銘柄別センチメント計算（score_news）
    - regime_detector.py : ETF MA とマクロニュースから市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py        : ETL パイプライン（run_daily_etl 等）
    - etl.py             : ETL 結果型の再エクスポート
    - news_collector.py  : RSS 取得・前処理・raw_news への保存支援
    - calendar_management.py : 市場カレンダー管理（営業日判定・更新ジョブ）
    - quality.py         : データ品質チェック（欠損・スパイク等）
    - stats.py           : 統計ユーティリティ（zscore_normalize）
    - audit.py           : 監査ログスキーマの DDL 定義・初期化
  - research/
    - __init__.py
    - factor_research.py : モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py : 将来リターン・IC 計算・統計サマリー
  - research パッケージは data.stats を使用して正規化やサマリーを行います

補足:
- デフォルトの DuckDB ファイル: data/kabusys.duckdb（settings.duckdb_path）
- 監視用 SQLite: data/monitoring.db（settings.sqlite_path）

---

## セキュリティ・運用上の注意

- ニュース収集モジュールは SSRF 対策（スキーム検証、リダイレクト先のプライベートアドレス検査、最大受信サイズ制限）を実装していますが、運用環境のネットワークポリシーも併せて確認してください。
- OpenAI / J-Quants API のキーは安全に保管し、ログに出力しないでください。
- 自動売買を行う場合は paper_trading（KABUSYS_ENV=paper_trading）で十分に検証してから live に切り替えてください。
- DuckDB のスキーマや ON CONFLICT の挙動は使っている DuckDB バージョンに依存する場合があります。プロダクション環境ではバージョン固定を推奨します。

---

## 開発・テスト

- モジュール内部は外部呼び出し部分（HTTP / OpenAI 呼び出し）をモック可能な設計です。ユニットテストでは関数ごとに外部通信を差し替えて検証してください。
- .env 自動ロード機能はテストで邪魔になる場合があるため、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能です。

---

もし README に追加したい具体的な使い方（例: バッチスクリプト、Docker 化、CI ワークフロー）や、補足の環境例（.env.example のテンプレート）などがあれば教えてください。README をそれに合わせて拡張します。