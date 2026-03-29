# KabuSys

日本株向けのデータプラットフォームと自動売買リサーチ基盤のコアライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を用いたセンチメント分析）、因子計算・特徴量探索、監査ログ（オーダー/約定トレーサビリティ）などを提供します。

---

## 主要機能

- ETL（J-Quants API 連携）
  - 株価日足（OHLCV）・財務データ・JPX カレンダーの差分取得と DuckDB への冪等保存
  - ETL 結果（ETLResult）と品質チェックの統合
- データ管理
  - market_calendar の営業日判定 / 翌営業日・前営業日演算
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - データ取得クライアント（J-Quants）: レート制御・自動リフレッシュ・リトライ
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別 ai_score）スコア化
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事の LLM センチメント）
- 研究（research）
  - モメンタム / バリュー / ボラティリティ系ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計まとめ
  - Zスコア正規化ユーティリティ
- 監査（audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化
  - 監査DB（DuckDB）初期化ユーティリティ（UTC タイムスタンプ固定）

---

## 前提 / 必要環境

- Python 3.10+（型注釈に Python 3.10 の構文を使用）
- 主要な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS 等）

（プロジェクトの requirements.txt がある場合はそれを使ってください）
例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

最低限の手動インストール例:
```bash
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

このパッケージは環境変数（またはプロジェクトルートの `.env` / `.env.local`）から設定を読み込みます。自動で .env を読み込む動作は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)  
  Slack 通知チャンネル ID
- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)  
  ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY (必要に応じて)  
  OpenAI を使う機能（news_nlp, regime_detector）で参照されます。関数呼び出しで明示的に api_key を渡すことも可能。

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-....
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

.env の自動読み込み順序:
1. OS 環境変数（優先）
2. .env.local（存在すれば上書き）
3. .env

自動読み込みを無効化する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（requirements.txt がある前提）
4. `.env` を作成し必要な環境変数を設定
5. DuckDB 用ディレクトリ作成（例: data/）
```bash
mkdir -p data
```

例:
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 存在する場合
# .env を編集してトークン等を設定
mkdir -p data
```

---

## 使い方（代表的な API / 実行例）

以下は Python REPL やスクリプトで直接呼び出す例です。関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- 単独で株価差分 ETL 実行
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュースセンチメントをスコア化（ai_scores へ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 因子計算（research）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査DB 初期化（監査用 DuckDB ファイル作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意:
- OpenAI を使う関数は api_key を明示的に渡すことができます。渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- 主要な関数は「ルックアヘッドバイアス」を避ける設計になっており、内部で date.today() を参照せず、呼び出し側から target_date を渡すことが推奨されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py              - パッケージ宣言、バージョン
- config.py                - 環境変数 / 設定読み込みロジック（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py            - ニュースの LLM スコアリングと ai_scores 書き込みロジック
  - regime_detector.py     - ETF MA200 + ニュースで市場レジームを判定
- data/
  - __init__.py
  - jquants_client.py      - J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py            - ETL パイプライン（run_daily_etl 等）
  - etl.py                 - ETLResult の再公開
  - news_collector.py      - RSS 取得 / 前処理 / raw_news 保存ロジック
  - calendar_management.py - market_calendar の管理・営業日計算
  - stats.py               - 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py             - データ品質チェック群（欠損・スパイク等）
  - audit.py               - 監査テーブル DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py     - モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py - 将来リターン / IC / 統計サマリー 等

その他:
- data/ ディレクトリ（DuckDB ファイル等のデフォルト配置先）

---

## 注意事項・運用上のポイント

- 環境設定は OS 環境変数を優先します。機密情報は .env に置く際はファイルのアクセス権に注意してください。
- OpenAI 呼び出しにはレートや課金が関係します。テスト時はモック（unittest.mock.patch）で外部呼び出しを差し替えてください。
- J-Quants の API レート（120 req/min）に配慮した実装になっています。大量取得や短期間のループ呼び出しは控えてください。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーとなる箇所があるため、実装は空チェックを行っています。
- news_collector は SSRF 対策や XML 爆弾対策（defusedxml）を組み込んでいますが、運用時に RSS ソースの信頼性を評価してください。

---

必要であれば、README に含める具体的な .env.example や CI / デプロイ手順、テストの実行方法（ユニットテスト・モック例）を追加で作成できます。どの追加情報が欲しいか教えてください。