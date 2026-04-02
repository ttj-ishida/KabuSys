# KabuSys

日本株向けのデータプラットフォーム／リサーチ／自動売買補助ライブラリです。  
DuckDB をデータ層に用い、J-Quants / OpenAI 等の外部 API と連携して以下を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の機能群を持つ Python パッケージです。

- データ収集（J-Quants から株価・財務・カレンダー取得、RSS ニュース収集）
- ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュースに基づく NLP スコアリング（OpenAI）
- 市場レジーム判定（移動平均乖離 + マクロニュースセンチメント）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 計算）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 汎用ユーティリティ（統計・カレンダー判定等）

注意: パッケージ自体は発注（実際の約定送信）を内包していません。取引実行を行う場合は責任を持って別層で実装してください。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info）
  - DuckDB への冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- data.pipeline
  - 日次 ETL 実行（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 実行結果を表す ETLResult
- data.quality
  - 欠損、重複、スパイク、日付不整合の検査（run_all_checks 等）
- data.news_collector
  - RSS 取得・パース・前処理・raw_news への保存（SSRF 対策、トラッキングパラメータ除去等）
- ai.news_nlp / ai.regime_detector
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（score_news）
  - ETF（1321）200日移動平均乖離とマクロニュースを合成して市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン算出（calc_forward_returns）、IC / 統計サマリ（calc_ic, factor_summary）
- data.audit
  - 監査ログテーブル定義 / 初期化（init_audit_schema, init_audit_db）
- config
  - .env / 環境変数から設定を読み込む Settings（settings オブジェクト）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）
- 外部 API アクセスに必要な資格情報（環境変数を使用）

pip 等で必要なパッケージをインストールしてください（requirements.txt をプロジェクトに追加している想定）。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / あるいはパッケージソースを配置
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   pip install -e .        # 開発インストール（setup が存在する場合）
   または
   pip install duckdb openai defusedxml
4. 環境変数の設定
   - プロジェクトルートに .env ファイルを置くと自動で読み込まれます（.git または pyproject.toml を基準に探索）。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   必須の環境変数（少なくともテストで使うもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード（本コードベースでは設定参照のみ）
   - SLACK_BOT_TOKEN — Slack 通知に使用するトークン
   - SLACK_CHANNEL_ID — Slack チャネル ID
   - OPENAI_API_KEY — OpenAI 呼び出しに必要（score_news / score_regime 等）
   省略可能な設定（デフォルトあり）
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH, 各種閾値, KABUSYS_ENV, LOG_LEVEL などは Settings クラス参照

.env の読み方やパースの挙動は kabusys.config に記載されています（export 形式やクォート対応あり）。

---

## 使い方（サンプル）

以下は最小限の Python からの呼び出し例です。DuckDB 接続を渡して API を使います。

1) ETL（日次 ETL 実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} stocks")
```

3) 市場レジーム判定（1321 の MA200 とマクロ記事の組合せ）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査用 DB 初期化（監査ログ専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.duckdb")
# 返り値は duckdb.DuckDBPyConnection
```

5) 研究用関数（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict リスト
```

注意:
- OpenAI を使う関数は api_key 引数を受け取れます（None の場合は環境変数 OPENAI_API_KEY を参照）。
- これらの関数は「ルックアヘッドバイアス」を避ける設計になっており、内部で date.today() を参照しない関数が多いです。バックテスト用途でも使いやすく設計されています。

---

## 設定 / 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 認証用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（score_news, score_regime 等）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に '1' を設定

設定は kabusys.config.settings オブジェクト経由で取得できます。
例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py                 (パッケージ定義, __version__ = "0.1.0")
  - config.py                   (.env/環境変数管理, Settings)
  - ai/
    - __init__.py
    - news_nlp.py               (ニュース NLP スコアリング: score_news)
    - regime_detector.py        (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py         (J-Quants API クライアント, 保存関数)
    - pipeline.py               (ETL パイプライン, run_daily_etl 等)
    - etl.py                    (ETLResult の再エクスポート)
    - calendar_management.py    (市場カレンダー管理)
    - stats.py                  (統計ユーティリティ / zscore_normalize)
    - quality.py                (品質チェック: missing/spike/duplicates/ date_consistency)
    - audit.py                  (監査ログスキーマ初期化 / init_audit_db)
    - news_collector.py         (RSS 収集 / 前処理)
  - research/
    - __init__.py
    - factor_research.py        (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py    (calc_forward_returns / calc_ic / factor_summary / rank)
  - research/* (ユーティリティ)
  - その他ユーティリティモジュール

（実際のリポジトリでは README の他に tests や docs などがある想定です）

---

## 運用上の注意

- 外部 API（J-Quants, OpenAI）呼び出しはレート制限・リトライ・エラーハンドリングを含む設計ですが、API キーやネットワーク状況に依存します。実運用時は適切な監視とレート管理を行ってください。
- news_collector は SSRF 対策や受信サイズ制限、XML パースの安全化を行っていますが、外部 RSS の扱いには常に注意が必要です。
- score_news / score_regime は LLM を利用するため、プロンプトやモデル・結果は継続的に監視し、品質の確認を行ってください。API 失敗時はフェイルセーフ（スコア 0.0 等）で動作しますが、想定外の結果が出る可能性があります。
- audit モジュールは監査ログを永続化する設計です。データ削除やスキーマ変更は慎重に行ってください。

---

## 貢献・拡張

- 新しいフィードの追加は data/news_collector.DEFAULT_RSS_SOURCES を増やし、fetch_rss / 保存ロジックを利用してください。
- 研究向けファクターは research パッケージに追加できます。返り値は既存の形式（date, code を含む dict リスト）に合わせると downstream と統合しやすいです。
- テストは各モジュールの外部依存（HTTP / OpenAI / DuckDB）をモックして行ってください。config.py は自動 .env ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意しています。

---

問題や詳しい使い方の追加ドキュメントが必要であれば、どの機能について深掘りしたいか教えてください。README のサンプルスクリプトや .env.example も作成できます。