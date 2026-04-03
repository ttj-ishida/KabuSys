# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注フローのトレーサビリティ）などを揃えています。

バージョン: 0.1.0

---

## 主要機能

- 環境変数 / .env の読み込みと一元管理（kabusys.config）
- J-Quants API クライアント（データ取得・保存・認証・レート制御） - kabusys.data.jquants_client
- 日次 ETL パイプライン（価格 / 財務 / カレンダー、品質チェック） - kabusys.data.pipeline
- データ品質チェック（欠損・重複・スパイク・日付不整合） - kabusys.data.quality
- ニュース収集（RSS、SSRF 対策、正規化、DB 保存） - kabusys.data.news_collector
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア） - kabusys.ai.news_nlp
- 市場レジーム判定（ETF とマクロニュースの組合せ） - kabusys.ai.regime_detector
- リサーチ用ファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ、IC、統計要約） - kabusys.research
- 監査ログ / トレーサビリティ（信号 → 発注 → 約定を追跡） - kabusys.data.audit
- 汎用統計ユーティリティ（Zスコア正規化など） - kabusys.data.stats

---

## 動作前提 / 必要環境

- 推奨 Python: 3.10+
- 主な依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、RSS フィードへのアクセスが必要な機能があります。

インストール方法はプロジェクト運用に合わせてください（pip / poetry 等）。簡易的には仮想環境を作成して必要パッケージをインストールします:

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# あるいは requirements.txt があれば:
# pip install -r requirements.txt
```

（パッケージ配布用の setup/pyproject.toml を用意している場合は `pip install -e .` 等でインストールします）

---

## 環境変数 / 設定

kabusys.config.Settings 経由で設定値を取得します。自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（優先順: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード（本システムの一部機能で使用）

- OPENAI_API_KEY  
  OpenAI API キー（score_news / score_regime などで参照。引数で上書き可能）

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID  
  LINE 通知用（任意）

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)  
  DuckDB ファイルパス

- SQLITE_PATH (デフォルト: data/monitoring.db)  
  監視や軽量永続化用 SQLite パス

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT  
  監視 / 実行管理に関連する設定

- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)  
  実行モード

- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)

例 `.env`（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（開発 / 動作確認）

1. リポジトリをクローン / ワークディレクトリに移動
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb / openai / defusedxml 等）
4. プロジェクトルートに `.env` を作成し必須の環境変数を設定
5. DuckDB の初期スキーマが必要な場合は適宜初期化（監査 DB 初期化等はコード例参照）

---

## 使い方（主要な API と例）

以下は Python からの利用例です。各関数は DuckDB 接続（duckdb.connect(...)）を受け取ることが多く、Look-ahead バイアスを防ぐため target_date を明示する設計です。

共通: DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL 実行（価格 / 財務 / カレンダー取得 + 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュース NLP（前日15:00 JST ～ 当日08:30 JST のウィンドウに対するスコアリング）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定可能
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込み銘柄数:", n_written)
```

市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに日次結果を書き込みます
```

監査ログ DB の初期化（監査専用 DuckDB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って signal_events / order_requests / executions テーブルが利用可能
```

J-Quants からの手動データ取得例:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

id_tok = get_id_token()  # settings.jquants_refresh_token を用いて取得
records = fetch_daily_quotes(id_token=id_tok, date_from=date(2026,3,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
```

品質チェックの実行:
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

環境変数自動ロードをテストで無効化する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュールと役割の一覧です（コードベースに基づく抜粋）。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースの LLM スコアリング・バッチ処理
    - regime_detector.py     -- 市場レジーム判定ロジック（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
    - pipeline.py            -- 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL の公開型（ETLResult の再エクスポート）
    - quality.py             -- データ品質チェック
    - news_collector.py      -- RSS 取得・前処理・保存（SSRF 対策等）
    - calendar_management.py -- マーケットカレンダーの管理・営業日判定
    - audit.py               -- 監査ログ（表定義・初期化）
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（モメンタム/バリュー/ボラ）
    - feature_exploration.py -- 将来リターン・IC・統計サマリー等

（上記以外に strategy / execution / monitoring 等のパッケージが __all__ に含まれていますが、ここに示したのは提供されたコードから確認できる主要部分です。）

---

## 設計上の注意事項 / 運用メモ

- Look-ahead バイアス対策:
  - 多くの関数は内部で `date.today()` を参照せず、呼び出し側が明示的に `target_date` を渡す想定です。バックテストや再現性を保つために必ず日付を明示してください。
- 冪等性:
  - J-Quants から取得したデータは DuckDB へ `ON CONFLICT DO UPDATE` で保存するため、再投入に対して冪等。
- OpenAI 呼び出し:
  - API エラーやレート制限に対してリトライやフェイルセーフ（スコア 0.0 にフォールバック）を行う実装です。ただしコスト・レート制限を運用で管理してください。
- RSS 取得:
  - SSRF 対策・サイズ制限・XML パース安全化（defusedxml）などに注意を払っています。
- テスト:
  - 自動 .env 読み込みはテストで影響が出る場合があるため `KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化を用意しています。

---

## 付録: よく使う関数の参照先

- ETL / 日次処理: kabusys.data.pipeline.run_daily_etl
- ニューススコア: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- J-Quants 操作: kabusys.data.jquants_client (get_id_token, fetch_daily_quotes, save_daily_quotes, fetch_market_calendar, save_market_calendar)
- 監査ログ初期化: kabusys.data.audit.init_audit_db / init_audit_schema
- 品質チェック: kabusys.data.quality.run_all_checks

---

不明点や README に追記してほしい項目（例: インストール方法を pyproject.toml / poetry に合わせた具体例、CI/デプロイ手順、追加のサンプルスクリプト）があれば教えてください。README をその運用フローに合わせて調整します。