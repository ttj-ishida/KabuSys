# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームのライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、AI を使ったニュースセンチメント評価、リサーチ用ファクター計算、そして監査ログ（発注・約定トレース）など、トレーディングシステム構築に必要なコンポーネントを備えます。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を中心としたローカル DB ベースの ETL / 集計
- API 呼び出しに対する堅牢なリトライ / レート制御
- LLM 呼び出しは JSON Mode を利用し、フェイルセーフ設計（失敗時は中立スコア 0 等で継続）
- 監査ログは冪等・追跡可能（UUID 連鎖）に設計

---

## 機能一覧

- 環境変数 / .env 自動ロード（`kabusys.config`）
- J-Quants API クライアント（取得・保存・認証・レート制御）
  - 日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - マーケットカレンダー取得・保存
- ETL パイプライン（差分取得 / バックフィル / 品質チェック）
  - 日次 ETL の実行エントリポイント `run_daily_etl`
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev 等）
- ニュース収集（RSS、SSRF 対策、前処理、raw_news 保存）
- AI モジュール（OpenAI）
  - ニュースセンチメント評価（銘柄別）`score_news`
  - 市場レジーム判定（ETF 1321 MA200 とマクロ記事の組合せ）`score_regime`
- 研究（Research）モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- 監査ログ（signal_events, order_requests, executions）の初期化・DB 作成・インデックス付与

---

## 前提 / 必要環境

- Python 3.10 以上（Union 型 `|` を使用しているため）
- 必要な Python パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

推奨: 仮想環境を作成してインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または requirements.txt がある場合: pip install -r requirements.txt
```

---

## 環境変数

必須（利用する機能による）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN : Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャネル ID
- OPENAI_API_KEY : OpenAI を使う機能（news_nlp / regime_detector）で必要

任意 / 設定
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 (development / paper_trading / live)
- LOG_LEVEL : ログレベル (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に `1` を設定

自動 .env ロード
- パッケージはプロジェクトルート（.git または pyproject.toml 見つかれば）を探索し、`.env` → `.env.local` を自動で読み込みます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール
   - pip install -r requirements.txt もしくは個別インストール（duckdb, openai, defusedxml など）
4. 環境変数を設定する（.env を作成）
   - 例: .env に `JQUANTS_REFRESH_TOKEN=...` `OPENAI_API_KEY=...` を設定
5. DuckDB データベースを初期化（必要に応じて）
   - 監査DB 初期化例は下記参照

---

## 使い方（代表的な例）

※ 以下は Python から直接呼び出す例です。エントリポイントや CLI がある場合はそちらに合わせてください。

- DuckDB 接続を作る（ファイル: data/kabusys.duckdb を想定）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を生成する（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", count)
```

- 市場レジーム判定を行う
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って signal/order/execution の操作・参照が可能
```

- J-Quants の生データ取得（単独で使う場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# id_token は get_id_token() で取得（環境変数 JQUANTS_REFRESH_TOKEN が必要）
quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

ログ・例外
- 各モジュールは logging を利用します。必要に応じてロガーを設定してください（`LOG_LEVEL` 環境変数でも制御）。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント / OpenAI 呼び出し
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - etl.py                        — ETL 公開インターフェース
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - stats.py                      — zscore 正規化等統計ユーティリティ
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログ（DDL / 初期化 / init_audit_db）
    - jquants_client.py             — J-Quants API クライアント（取得/保存/認証）
    - news_collector.py             — RSS 収集・前処理・raw_news 保存
    - etl.py                        — （パイプライン再エクスポート）
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 等
    - feature_exploration.py        — 将来リターン / IC / summary
  - monitoring/ (存在を想定するモジュール群: プロセス監視等)
  - strategy/  (戦略本体、Signal 生成など - 実装は別にある想定)
  - execution/ (約定 / ブローカーインターフェース - 実装は別にある想定)

上記ファイル群は主要な機能毎に分割され、DuckDB と SQL + Python の組合せで効率的に処理を行うよう設計されています。

---

## 注意点 / 運用メモ

- OpenAI の呼び出しは API レートやコストが発生します。テストではモック化が容易なように内部呼び出しをラップしてあります（ユニットテスト時は `_call_openai_api` をパッチする等）。
- J-Quants API はレート制限と認証トークンの更新ロジックを備えていますが、実運用では API 利用制限に注意してください。
- DuckDB に保存するスキーマ（テーブル）や列はモジュール側で前提されています。初回は必要なスキーマを作成してから ETL を実行してください（スキーマ初期化ユーティリティを別途用意することを推奨）。
- ニュース収集では SSRF 対策・受信サイズ制限等を組み込んでいますが、公開環境では更に監視・ログを強化してください。
- 本 README はコードベースの概要と基本的な使い方をまとめたものです。詳細な API 仕様やスキーマ定義はソース内のドキュメント文字列（docstring）を参照してください。

---

必要であれば、以下を追加で作成します：
- requirements.txt / pyproject.toml の推奨内容
- 初期スキーマ作成スクリプト（raw_prices などの DDL）
- よく使う CLI ラッパーや systemd / supervisor 用のサービス説明

ご希望があれば教えてください。