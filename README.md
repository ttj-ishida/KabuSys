# KabuSys — 日本株自動売買システム

※この README はリポジトリ内のコード構成（src/kabusys 以下）をもとに作成した開発者向けの概要・導入・利用ガイドです。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォームおよび自動売買基盤のコアライブラリです。  
主に以下を提供します：

- J-Quants からのデータ取得 / ETL（株価日足・財務・マーケットカレンダー）
- ニュース収集と LLM を用いたニュースセンチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- 研究用ファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「フォールバック（カレンダー未取得時の曜日判定等）」「API リトライ・レート制御」「監査可能なデータ保存」を重視しています。

---

## 主な機能一覧

- データ収集 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）：レート制御・リトライ・ページネーション対応
- ニュース処理 / LLM スコアリング
  - RSS 収集・前処理・保存（kabusys.data.news_collector）
  - ニュースを銘柄別に集約して OpenAI（gpt-4o-mini）でスコア化（kabusys.ai.news_nlp）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成（kabusys.ai.regime_detector）
- 研究・ファクター
  - モメンタム / バリュー / ボラティリティ等のファクター計算（kabusys.research）
  - forward returns、IC、統計サマリー等のユーティリティ
- データ品質チェック（kabusys.data.quality）
- 監査ログスキーマ初期化 / 監査 DB 作成（kabusys.data.audit）

---

## 動作要件（概略）

- Python 3.10 以上（typing の構文などを使用）
- 必要なパッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらに従ってください）

インストール例（環境によって仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# （パッケージ配布があれば）pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする
2. Python 仮想環境を作成して依存パッケージをインストール
3. プロジェクトルートに `.env` を作成（下記参照）
   - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から自動で .env を読み込みます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい（テスト等で利用）。
4. 必要に応じて DuckDB ファイルや監査 DB のディレクトリを作成

.env の例（プロジェクトルートに保存）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API（発注連携など）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI API
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# DB パス（デフォルトは data/kabusys.duckdb / data/monitoring.db）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

必須環境変数:
- JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD（kabuステーション連携が必要な場合）

OpenAI を使う操作（news scoring / regime scoring）を行う場合は:
- OPENAI_API_KEY を環境変数に設定するか、各関数に api_key を渡してください。

---

## 使い方（主なユースケース）

以下は Python REPL やスクリプトから呼び出す最小例です。適宜 logging 設定を行ってください。

- DuckDB 接続の作成（データ格納用 DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム（bull/neutral/bear）の判定と書き込み
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- ファクター計算・研究ユーティリティの利用例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum_records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore_normalize は kabusys.data.stats に実装
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "mom_6m"])
```

- データ品質チェック（ETL 後に自動で run_daily_etl が実行しますが個別にも可能）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- LLM 呼び出し（OpenAI）は費用とレートに注意して利用してください。score_news / score_regime は API 失敗時にフェイルセーフ（0.0 等）で継続する設計です。
- DuckDB のバージョン互換性に注意（executemany の挙動など）。ログや警告を参照してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理・営業日ロジック
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS 取得・前処理・保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査スキーマ初期化 / init_audit_db
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns / IC / factor_summary / rank
  - ai/ (上記)
  - research/ (上記)
  - その他モジュール群（strategy / execution / monitoring は __all__ に設定されているが、この抜粋には含まれていません）

---

## 開発・運用上の注意

- 環境変数は .env（プロジェクトルート）で管理可能。config モジュールは .git または pyproject.toml に基づいてプロジェクトルートを探索します。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで便利）。
- OpenAI の呼び出しはレスポンスのバリデーションとリトライを行いますが、コストとレートに注意して運用してください。
- ETL は「差分更新＋バックフィル」を行い、品質チェックは Fail-Fast ではなく全件収集する設計です。
- DuckDB へ接続する際はファイルパスの親ディレクトリが存在することを確認してください（audit.init_audit_db は必要に応じて親ディレクトリを自動作成します）。

---

## 参考（よくあるコマンド）

- 仮想環境作成・依存インストール
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt  （ある場合）
- Python スクリプトを使った ETL 実行（例）
  - python -c "from kabusys.data.pipeline import run_daily_etl; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(run_daily_etl(conn, datetime.date(2026,3,20)).to_dict())"

---

必要に応じて README を拡張して CI / デプロイ手順（systemd service での常駐実行、監視設定、LINE 通知設定例など）やさらに詳しい API ドキュメント（各関数の引数・戻り値・例外）を追加できます。どの部分を詳しく書きたいか指示をください。