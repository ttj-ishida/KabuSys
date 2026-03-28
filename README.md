# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（ミニマム実装）。  
J‑Quants API や RSS を用いたデータ収集、DuckDB ベースの ETL、ニュースの LLM センチメント、ファクター計算、監査ログ（オーダー→約定トレース）などを提供します。

- 開発版のパッケージ名空間: `kabusys`
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主要機能一覧

- データ収集 / ETL
  - J‑Quants からの株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- カレンダー管理
  - 市場営業日判定、前後営業日取得、期間内営業日取得、SQ判定、夜間カレンダー更新ジョブ

- ニュース収集・前処理
  - RSS 収集（SSRF・gzip・受信サイズ制限・トラッキングパラメータ除去）
  - raw_news への冪等保存と銘柄紐付け

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM でスコア化（JSON Mode, バッチ・リトライ実装）
  - マクロニュース + ETF MA による市場レジーム判定（bull / neutral / bear）

- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター算出
  - 将来リターン計算、IC（Spearman）やランク付け、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ、初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止

- 設定管理
  - .env ファイル自動ロード（プロジェクトルート検出）と環境変数アクセスラッパー（settings）

---

## 必要・推奨環境

- Python 3.10+
  - （型注釈に `|` を使っているため 3.10 以上を想定）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - （HTTP および標準ライブラリで多くの処理を行います）
- ネットワークアクセス: J‑Quants API、OpenAI API、RSS ソース

依存はプロジェクトの packaging によりますが、開発環境では次を参考にインストールしてください（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
pip install -e .   # パッケージ化されていれば
```

---

## 環境変数（主なもの）

必須（少なくとも ETL / 発注 / Slack 通知等を使う場合）:

- JQUANTS_REFRESH_TOKEN — J‑Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）

任意 / デフォルトあり:

- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト `INFO`
- DUCKDB_PATH — DuckDB のパス。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — 監視用 SQLite パス。デフォルト `data/monitoring.db`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` をセットすると .env 自動ロードを無効化

プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（ただしテスト時などで無効化可）。

---

## セットアップ手順（ローカルでの最小手順）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存をインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   pip install -e .
   ```

4. .env を作成（プロジェクトルート）
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   KABU_API_PASSWORD=...
   # 必要に応じて DUCKDB_PATH, KABUSYS_ENV などを追加
   ```

5. DuckDB ファイルの親ディレクトリを作る（自動で作成する関数もありますが手動でも）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

注意: ここでは簡単な利用例のみ記載します。各関数は詳細な docstring が付与されています。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続を作って ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄単位）を LLM でスコア化
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を省略すると環境変数 OPENAI_API_KEY を使用
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（監査用 DB を別途作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order / execution のテスト挿入などが可能
```

- 研究機能（ファクター計算 / 正規化 / IC）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# zscore_normalize を使って正規化など
```

---

## 注意点 / 設計方針（主なもの）

- Look-ahead バイアス対策: 多くの関数は内部で現在時刻を直接参照せず、明示的な target_date を受け取ります。バックテスト時は必ず target_date を制御してください。
- 冪等性: 多くの保存関数は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE を用いて冪等に実装されています。
- OpenAI 呼び出し: JSON Mode を期待したパースやリトライ実装が組み込まれています。API キーは引数で注入可能（テスト容易性のため）。
- RSS 取得: SSRF/圧縮爆弾/トラッキングパラメータ等に配慮した安全実装。
- DuckDB との互換性: 一部の実装（executemany の空リストなど）で DuckDB バージョン依存の注意を払っています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動ロードと Settings ラッパー
- ai/
  - __init__.py
  - news_nlp.py — 銘柄ニュースの LLM センチメント取得・ai_scores 書き込み
  - regime_detector.py — マクロ + ETF MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS 収集と前処理
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py — データ品質チェック群
  - audit.py — 監査スキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

（フルのファイルは src/kabusys 以下に多数実装されています。README のこの抜粋は主要モジュールが分かるようにまとめたものです。）

---

## テスト / デバッグのヒント

- 自動で .env をロードする機能は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（ユニットテストで .env に依存させない場合に便利）。
- OpenAI API 呼び出しや外部ネットワーク呼び出し部分は個々の内部関数に分離してあり、ユニットテスト時はそれらをモック可能です（ソース中コメント参照）。
- DuckDB をインメモリ（":memory:"）で初期化してユニットテストを実行可能（audit.init_audit_db は ":memory:" を受け付けます）。

---

## ライセンス / コントリビューション

本 README ではライセンス情報を含めていません。実際のリポジトリでは LICENSE ファイルや CONTRIBUTING.md を参照してください。

---

必要であれば、各モジュールの API サンプル（関数ごとの短い使用例）や .env.example のテンプレート、推奨 requirements.txt を追記します。どの部分を詳しく示しましょうか？