# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
本ドキュメントはコードベース（src/kabusys 以下）に基づいた概観、セットアップ、使い方、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 主な機能
- 環境変数 / 設定
- セットアップ手順
- 使い方（代表的な API/ワークフロー例）
- ディレクトリ構成
- 注意点 / 実装上の設計意図

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・リサーチ（ファクター計算）・AI を用いたニュースセンチメント評価・市場レジーム判定・監査ログ（発注〜約定トレーサビリティ）などを包含するモジュール群です。  
主に下記の用途を想定しています。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー等）
- DuckDB を用いたローカルデータストア／ETL パイプライン
- ニュースの収集と LLM による銘柄センチメント算出
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用のファクター計算・IC/統計サマリ機能
- 発注／約定に関する監査テーブルの初期化・管理

設計上の特徴として、Look-ahead バイアス回避（バックテストでの不正な未来参照防止）や API リトライ・レート制御（J-Quants）・DuckDB への冪等保存などを重視しています。

---

## 主な機能（一覧）

- data/
  - J-Quants クライアント（取得・保存・認証・レート制御）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
  - ニュース収集モジュール（RSS 取得・前処理・SSRF 対策）
  - カレンダー管理（JPX カレンダー取得・営業日判定）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp: ニュースを銘柄ごとに LLM でセンチメント評価し ai_scores へ保存
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して market_regime を作成
- research/
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（スピアマンランク）、統計サマリなど
- config: 環境変数 / .env 自動読み込み・検証
- audit: 監査ログのテーブル DDL と初期化ユーティリティ

---

## 環境変数 / 設定（代表）

config.Settings クラスがアプリ設定を提供します。重要な環境変数は以下の通りです。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI（LLM）呼び出しに使用する API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV: 環境。`development`, `paper_trading`, `live` のいずれか
- LOG_LEVEL: ログレベル（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視関連パス

自動で .env / .env.local をロードします（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

※ここでは Python 環境が既に用意されている前提です（推奨: 3.10+）。

1. クローン / ソース配置
   - レポジトリをクローンし、プロジェクトルートに移動します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - 必要に応じてテストやログ用のパッケージを追加してください。

   （本リポジトリに requirements.txt がない場合は上記を目安にしてください）

4. 環境変数設定
   - プロジェクトルートに .env を作成して以下を設定（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb

   - あるいは OS 環境変数としてエクスポートしても可。

5. データベース用ディレクトリ作成
   - デフォルトでは `data/` に DuckDB ファイル等を置きます。必要であればディレクトリを作成してください。
     - mkdir -p data

6. （任意）監査ログ DB 初期化
   - 下記の API を使い、監査ログテーブルを初期化できます（詳細は「使い方」参照）。

---

## 使い方（代表的な例）

以下はライブラリを Python から呼び出す基本例です。実行環境は仮想環境で .env を読み込んだ状態を想定しています。

- 1) DuckDB 接続を開く / ETL を走らせる

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を明示することを推奨（Look-ahead バイアス回避）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 2) ニュースのスコアリング（ai.news_nlp.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を渡せる。渡さない場合は OPENAI_API_KEY 環境変数を参照
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 3) 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 4) 監査ログ DB の初期化（audit.init_audit_db / init_audit_schema）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を監査専用 DB として使う例
conn = init_audit_db(settings.duckdb_path)
# あるいは別パスで監査専用 DB を作成可能:
# conn = init_audit_db("data/audit.duckdb")
```

- 5) 研究系ユーティリティの呼び出し例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なモジュールとファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult re-export)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit.init_audit_db / init_audit_schema 等
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research (公開関数: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank)

各モジュールはドキュメンテーション文字列（docstring）で役割・設計方針が詳述されています。実装は主に DuckDB SQL と Python の組合せで書かれており、外部 API 呼び出し（OpenAI / J-Quants / RSS）部分にはリトライ・フェイルセーフの配慮があります。

---

## 注意点 / 実装設計のポイント

- Look-ahead バイアス回避:
  - 多くの関数は内部で date.today() を使わず、明示的な target_date 引数を要求するか、DB の最終日を基準に動作します。バックテストでの誤用に注意してください。
- J-Quants:
  - rate limit（120 req/min）を厳守するためモジュール内でスロットリングを行います。
  - 401 時は自動的にリフレッシュを試みます（1 回）／リトライは指数バックオフ。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定した JSON Mode を使用する実装になっています。API 呼び出しはリトライやレスポンス検証を行います。
- ニュース収集:
  - RSS の取得は SSRF 対策（リダイレクト検査・プライベートアドレス排除）・XML パースの安全対策（defusedxml）・受信サイズ制限などセキュリティ対策が組み込まれています。
- DuckDB との相互作用:
  - 保存処理は基本的に ON CONFLICT DO UPDATE で冪等性を確保します。exectutemany に空リストを渡せないバージョンの DuckDB に配慮した実装があります。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動的に読み込みます。テストなどでこれを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 追加情報 / トラブルシューティング

- 環境変数が不足している場合、config.Settings のプロパティは ValueError を投げます。.env.example（存在する場合）を参考に .env を作成してください。
- OpenAI API のレスポンスが期待する JSON 形式でない場合、ニューススコアの算出はフォールバックしてスキップしたり 0 を返す設計になっています（フェイルセーフ）。
- DuckDB のバージョンにより executemany 空リストの扱いなどが異なるため、エラーが出る場合は DuckDB バージョンを確認してください。
- ログレベルや閾値（CPU/メモリ/ディスク閾値など）は環境変数で調整できます。

---

README は以上です。より具体的な使用例や CLI、デプロイ手順（systemd / コンテナ化等）を追加したい場合は、用途（本番稼働、バックテスト、ローカル検証）に応じて追記可能です。必要であればサンプル .env.example や簡易 CLI ラッパーの雛形も作成します。