# KabuSys

日本株向けのデータプラットフォームおよび自動売買基盤コンポーネント群です。  
DuckDB ベースのデータレイヤー、J-Quants API クライアント、ニュース収集・NLP（OpenAI）連携、ファクター計算・リサーチ、監査ログ（発注/約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を想定したモジュール群です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（差分取得・冪等保存・品質チェック）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析と市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）
- kabuステーション等への発注実装の土台（execution 層）や監視設定を含む

本リポジトリは Python パッケージ（src/kabusys）として構成されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・ページネーション・リトライ・トークン自動リフレッシュ）
  - ニュース収集（RSS を安全に取得・正規化・raw_news へ保存）
  - マーケットカレンダー管理（営業日判定 / next/prev / calendar update job）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（news_nlp.score_news：銘柄単位のセンチメントを ai_scores に保存）
  - 市場レジーム判定（regime_detector.score_regime：ETF(1321) MA200 と LLM センチメントの合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境変数 / .env 自動読み込み、Settings オブジェクト（settings）による集中管理

---

## 必要条件

- Python 3.10 以上
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで実装されている箇所も多いですが、実行する機能に応じて追加依存が必要です）

（本リポジトリに requirements.txt / pyproject.toml がある場合はそちらに従ってください。）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージと依存関係インストール
   - 開発パッケージが用意されている場合:
     - pip install -e .
   - 最低限必要なライブラリを個別に入れる場合:
     - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（環境によって OS 環境変数が優先されます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI の API キー（ai モジュールを使う場合は必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携を使う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合
   - DUCKDB_PATH: デフォルト DB パス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: environment (development / paper_trading / live)
   - LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は代表的な使用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...)）を受け取る設計です。

- DuckDB に接続して ETL を実行する（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- AI ニューススコアリング（news_nlp）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用 DuckDB の作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- マーケットカレンダー判定ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- AI モジュールを使う場合は OPENAI_API_KEY を設定してください（または api_key 引数で渡す）。
- ETL / データ保存は冪等設計になっていますが、DuckDB のバージョンや環境によって挙動差が出る場合があります（executemany の空リストなど）。実運用前にテスト環境で動作確認してください。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージの主要ファイル・モジュール:

- kabusys/
  - __init__.py
  - config.py                : 環境変数・.env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            : ニュースセンチメント解析と ai_scores 書き込み
    - regime_detector.py     : 市場レジーム判定（MA200 + LLM）
  - data/
    - __init__.py
    - pipeline.py            : ETL パイプライン（run_daily_etl など）
    - jquants_client.py      : J-Quants API クライアント（fetch / save）
    - news_collector.py      : RSS 取得・前処理・raw_news への保存
    - calendar_management.py : 市場カレンダー管理（営業日判定・更新ジョブ）
    - quality.py             : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py               : zscore_normalize 等の統計ユーティリティ
    - audit.py               : 監査ログスキーマ定義・初期化
    - etl.py                 : ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py     : モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py : 将来リターン / IC / summary / rank
  - ai/ (上記)
  - research/ (上記)
  - その他: execution / monitoring / strategy などの名前が package export に含まれていることから、それらの層が存在する想定（本抜粋に含まれない場合もあります）

---

## 実運用上の注意事項

- 環境変数の管理: .env/.env.local を用いた自動読み込み機能があります。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索します。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Look-ahead Bias の防止: AI モジュール・ETL はルックアヘッドを避ける設計になっています（入力に target_date を明示、DB クエリは date < target_date / date <= target_date の扱いに注意）。
- 外部 API との連携: J-Quants や OpenAI の API キーは厳重に管理してください。J-Quants はレート制限を守る実装済みですが、実行頻度には注意してください。
- DuckDB バージョン: 一部の実装（executemany の挙動や型バインド）は DuckDB のバージョンに依存する可能性があります。互換性を確認してください。
- テスト: OpenAI 呼び出し等はテスト時にモック化が想定されています（モジュール内で _call_openai_api を差し替え可能）。

---

## 貢献・拡張

- 新しいデータソースの追加（RSS / API）や品質チェックの追加、発注ロジック（kabuステーション）との実装統合は容易に拡張可能です。
- research 層や strategy 層を追加してシグナル生成・バックテストと接続することでトレード自動化の全体フローを構築できます。

---

必要であれば、README にサンプル .env.example、DB スキーマ（DDL）やユースケース別のコマンド例（cron / systemd / docker-compose）を追記できます。どの情報を追加したいか教えてください。