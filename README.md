# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。ETL（J-Quants からのデータ取得）、ニュース NLP による銘柄センチメント評価、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時は安全なデフォルトで継続）」で、DuckDB をデータストアに使う想定です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（.env）
- ディレクトリ構成（主要ファイルと説明）
- 補足・注意点

---

プロジェクト概要
- 名前: KabuSys
- 説明: 日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群。J-Quants API や RSS からデータを取得して DuckDB に蓄積し、NLP（OpenAI）でニュースを解析、ファクター算出・品質チェック・監査ログを行う。
- 主な依存技術: Python (3.10+), duckdb, OpenAI SDK, defusedxml（RSSパース用）

---

機能一覧
- 環境設定管理
  - .env 自動読み込み（OS 環境変数 > .env.local > .env、無効化可能）
  - 各種パス・モード・閾値の管理（settings オブジェクト）
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT 相当）
- ETL パイプライン
  - 日次差分 ETL（calendar → prices → financials）、品質チェック組み込み
  - ETLResult に処理結果を集約
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日/非営業日）検出
- ニュース収集・前処理
  - RSS フィード取得、URL 正規化、SSRF 対策、記事 ID 生成、raw_news への冪等保存を想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約し gpt-4o-mini に送信、ai_scores へ保存（バッチ処理・リトライ）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントの重み付け合成）
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions などのテーブル定義と初期化ユーティリティ
  - 監査 DB の初期化 helper（UTC に固定）

---

セットアップ手順（開発ローカル向け）
1. Python のバージョンを用意
   - 推奨: Python 3.10 以上（型注釈で | を使用しているため）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml
   - 任意で logging 等は標準ライブラリで足ります
   - （プロジェクトに setup.py/pyproject.toml があれば pip install -e . を使ってもよい）
4. 環境変数（.env）を準備
   - ルートに .env（および必要なら .env.local）を配置するか OS 環境変数で設定
   - 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB データベース用ディレクトリ作成（settings.duckdb_path の親ディレクトリ）
   - デフォルトは data/kabusys.duckdb
6. （任意）監査用 DB 初期化サンプルは下記参照

---

環境変数（代表例）
- 必須（ETL 等を使う場合）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
  - OPENAI_API_KEY: OpenAI API キー（news NLP / regime 判定用）
- kabu（発注）関連
  - KABU_API_PASSWORD: kabu API のパスワード
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- ログ・環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH など監視用設定
- その他
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading のモック約定動作）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

使い方（主要な API の簡単な例）

- 共通準備
```python
from datetime import date
import duckdb
from kabusys.config import settings

# DuckDB 接続（ファイルパスは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（prices / financials / calendar を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が使われます
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使う）
```python
from kabusys.ai import score_news

count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- J-Quants API を直接呼ぶ一例
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))
saved = jq.save_daily_quotes(conn, quotes)
```

---

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理。settings オブジェクトを通じて利用。
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py: ニュースを銘柄毎にバッチして OpenAI でスコア化する実装
    - regime_detector.py: ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py: ETL のメイン処理（run_daily_etl 等）と ETLResult
    - etl.py: ETLResult の再エクスポート
    - calendar_management.py: JPX カレンダー管理と営業日判定ユーティリティ
    - news_collector.py: RSS 収集・前処理（SSRF 対策等）
    - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査（signal / order / execution）テーブル定義と初期化ロジック
  - research/
    - __init__.py
    - factor_research.py: momentum / value / volatility 等のファクター計算
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank
  - research や data に渡る補助モジュール群

---

補足・注意点
- Python バージョン: 3.10 以上を想定（型注釈に | を利用）
- .env 自動読み込み:
  - 実装はパッケージファイル位置からプロジェクトルートを探索し、.env → .env.local の順で読み込みます（OS 環境変数は常に最優先）。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定し JSON Mode を利用して厳密な JSON 出力を期待します。API 失敗時はフェイルセーフでスコア 0.0 やスキップを行います（例外を広げない設計の箇所あり）。
- DuckDB に関して:
  - 一部処理は executemany に空リストが渡せない（DuckDB 0.10 の制約）前提でガードしているため、古い/異なる DuckDB バージョンでの挙動に注意してください。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベートアドレス拒否）、defusedxml を使用した XML パースを実装していますが、運用時はさらに外部接続の制限や監査を行ってください。
- 本リポジトリには CLI スクリプトや systemd 用ユニットは含まれません。運用時は上の関数をラッパーするスクリプト / ワーカーを作成してください。

---

問い合わせ・貢献
- この README はコードベースから主要 API と設計方針をまとめたものです。実運用・デプロイにあたってはローカルでの動作確認（API キー・トークンの管理、定期ジョブの監視、バックアップ等）を必ず行ってください。
- バグ修正や機能追加の提案は Pull Request / Issue を通じて行ってください。

以上。README の追加項目（例えば CLI サンプル、docker-compose、テスト手順など）を希望される場合は用途に合わせて追記します。