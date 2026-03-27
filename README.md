# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLP評価、研究用のファクター計算、監査ログ設計、そして市場レジーム判定やニュースセンチメントを行うAI連携モジュールなどを含みます。

## 主な特徴
- J-Quants API を使った株価・財務・カレンダーの差分取得（ページネーション対応、リトライ、レート制御）
- DuckDB ベースの ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と前処理／NLP（OpenAI）による銘柄別センチメントスコア生成
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメント）
- 研究用ユーティリティ（モメンタム・バリュー・ボラティリティファクター、将来リターン、IC、統計サマリ等）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合など）

---

## 動作要件
- Python 3.10 以上（PEP 604 のユニオン型表記などを使用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を利用

（プロジェクト配布時に requirements.txt / pyproject.toml で管理する想定です）

---

## セットアップ手順（開発環境）
1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. 必要パッケージをインストール
   - 参考（最小セット）:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。
3. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。自動ロード機能により `.env.local` が `.env` より優先されます（OS 環境変数が最優先）。
   - 主要な環境変数（必須／用途）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI 呼び出しに使う API キー（AI モジュール利用時に必須）
     - DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 実行モード ("development" / "paper_trading" / "live")（デフォルト: development）
     - LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト時に便利）
   - サンプル `.env`（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
4. （任意）パッケージとして開発インストール
   ```bash
   pip install -e .
   ```
   ※ リポジトリのパッケージ配布方法に依存します。

---

## 使い方（主な API と例）

注意: 多くの関数は duckdb.DuckDBPyConnection を受け取ります。接続は `duckdb.connect(path)` で作成してください。

- DuckDB 接続の作成例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

### 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- run_daily_etl は market calendar → prices → financials → quality checks の流れで実行します。
- id_token を明示的に渡すことも可能（tests 等で便利）。

### ニュースセンチメント（銘柄ごとの ai_scores 生成）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡してください
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- score_news は raw_news / news_symbols / ai_scores テーブルを使い、最大バッチ 20 銘柄ずつ OpenAI に問い合わせて ai_scores を更新します。
- API キーは env の OPENAI_API_KEY または関数引数 api_key を使用。

### 市場レジーム判定（1321 MA200 乖離 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- OpenAI を利用するため OPENAI_API_KEY が必要（引数で渡すことも可）。
- 計算後、market_regime テーブルへ冪等書き込みを行います。

### 監査ログスキーマ初期化 / 監査用 DB の作成
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# または既存接続へスキーマ追加
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

### J-Quants API クライアント直接利用（フェッチ・保存）
```python
from kabusys.data import jquants_client as jq
from datetime import date

# 直接データを取得
quotes = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
# DuckDB に保存
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, quotes)
```

### 研究用ユーティリティの利用例
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 列の Z スコア正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 自動環境変数読み込みについて
- `kabusys.config` はプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージメタ情報（version, __all__）
- config.py — 環境変数/設定読み込みロジック（Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM ベースセンチメント処理（score_news 等）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL 結果クラスの再エクスポート（ETLResult）
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - news_collector.py — RSS 取得・正規化・raw_news 保存ロジック
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（DDL / init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum, Value, Volatility, Liquidity 等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数
- その他: モジュール間で読みやすい小分けされた実装になっています。

---

## 設計上の注意・挙動
- ルックアヘッドバイアス回避のため、多くのモジュールは内部で `date.today()` / `datetime.today()` を直接参照しません。処理対象日は明示的に渡す設計です。
- OpenAI 呼び出しは JSON モードを前提にし、リトライ・フォールバック（失敗時は中立スコア 0.0）等の堅牢性を備えています。
- J-Quants クライアントはレート制御、リトライ、401 リフレッシュ対応、ページネーション対応を実装しています。
- ETL は各ステップで例外を捕捉し、可能な限り他のステップを継続する設計（Fail-Fast ではない）。
- DuckDB を使うことでローカルかつ高速な分析用 DB を軽量に運用できます。

---

## よくある運用ユースケース
- 毎日の夜間バッチで run_daily_etl を実行し、prices / financials / calendar を更新 → その後 score_news / score_regime を実行して AI スコア・レジームを更新 → 研究チームや戦略がそれらを参照してシグナル生成。
- signal 発生時は監査テーブルに履歴を残し、order_requests を通じてブローカー発注・約定を監査可能にする。

---

## 参考 / トラブルシューティング
- OpenAI リクエスト失敗や JSON パースエラーは警告ログを残しフェイルセーフで中立値を採用する箇所が多くあります（運用時はログ監視を推奨）。
- DuckDB executemany は空リストを受け付けない場合があるため、実装側で空チェックがあります。ETL の戻り値を確認してください。
- news_collector は SSRF 対策、受信サイズ制限、XML パース安全化（defusedxml）などセキュリティ考慮済みです。

---

この README はコードベースの主要機能と利用手順の概要を記載しています。詳細な API 仕様や実運用向けの設定（CI / cron / Docker 化、監視・アラート、キー管理等）は別途ドキュメントにまとめてください。質問や特定の機能の利用例が必要であれば教えてください。