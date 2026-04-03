# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ（プロトタイプ）。  
ETL、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター研究、監査ログ（発注→約定トレーサビリティ）、市場レジーム判定などを含むモジュール群を提供します。

バージョン: 0.1.0

## 概要
KabuSys は以下の役割を想定した Python モジュール群です。

- J-Quants API からのデータ取得（株価、財務、JPXカレンダー）
- DuckDB を用いた永続化（raw_prices / raw_financials / market_calendar / ai_scores / …）
- ニュース収集（RSS）と LLM による銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- ETL パイプライン（差分取得・保存・品質チェック）

設計では「ルックアヘッドバイアスの防止」「DB へ冪等に保存」「外部 API の失敗はフェイルセーフで継続」等に配慮しています。

## 主な機能一覧
- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - pipeline: 日次 ETL 実行（run_daily_etl 等）
  - news_collector: RSS 収集・前処理（SSRF 対策・トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク等）
  - calendar_management: JPX カレンダーの判定・更新ロジック
  - audit: 監査ログテーブルの初期化ユーティリティ
  - stats: zscore 正規化など
- ai/
  - news_nlp: ニュースをまとめて LLM へ投げ、ai_scores テーブルへ書き込む処理（score_news）
  - regime_detector: ETF（1321）MA とマクロニュースを合成して市場レジームを判定（score_regime）
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター算出
  - feature_exploration: 将来リターン計算、IC、統計サマリ等

## 前提条件
- Python 3.10+
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API トークン（リフレッシュトークン）
- OpenAI API キー（ニュース NLP / レジーム判定で使用する場合）

※ 実運用ではネットワークアクセス可能な環境と J-Quants / OpenAI の利用契約が必要です。

## セットアップ手順（開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```
2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 依存関係をインストール
   - requirements.txt 等がない場合は最低限以下をインストールしてください。
   ```
   pip install duckdb openai defusedxml
   ```
   - パッケージとしてインストールする場合（開発モード）:
   ```
   pip install -e .
   ```
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（src/kabusys/config.py が自動ロード）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合必須）
     - KABU_API_PASSWORD: kabu API パスワード（kabu ステーション連携用）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   .env の例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pw
   DUCKDB_PATH=data/kabusys.duckdb
   ```

## 使い方（コード例）
以下はライブラリを直接インポートして使う最小例です。DuckDB の接続は duckdb.connect で作成します。

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None -> OPENAI_API_KEY を参照
print(f"書込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンがセットされます
```

- 設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # development/paper_trading/live
```

### 注意点・フェイルセーフ
- OpenAI / J-Quants の API 呼び出しはリトライやフォールバックが実装されていますが、APIキーがない場合は関数は ValueError を投げます（api_key 引数または環境変数 OPENAI_API_KEY を設定してください）。
- ETL や NLP は外部 API に依存するため、テストではモック（unittest.mock.patch）を使うことを推奨します。score_news や regime_detector の内部 API 呼び出し `_call_openai_api` をモック可能です。
- .env の自動読み込みはプロジェクトルート基準で行われます（config._find_project_root）。テスト中に制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須 for J-Quants client)
- OPENAI_API_KEY (必要に応じて)
- KABU_API_PASSWORD (kabu API 用)
- KABUSYS_ENV (development / paper_trading / live) — validation あり
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH 等（監視設定用）

## ディレクトリ構成（主なファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数 / .env 自動ロード・設定ラッパー
    - ai/
      - __init__.py
      - news_nlp.py — ニュースの LLM スコアリング（score_news）
      - regime_detector.py — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py — J-Quants API クライアント（fetch/save 系）
      - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
      - etl.py — ETLResult エクスポート
      - news_collector.py — RSS 収集・前処理
      - calendar_management.py — JPX カレンダー判定・更新
      - quality.py — データ品質チェック
      - stats.py — zscore_normalize 等
      - audit.py — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py — モメンタム/ボラティリティ/バリュー等
      - feature_exploration.py — 将来リターン/IC/統計サマリ
    - monitoring/, strategy/, execution/ ...（パッケージ公開用 __all__ に含むが、今回のコードベースでは一部実装）
- pyproject.toml / .git / .env.example (プロジェクトルートに存在する想定)

（上記はソースの主要モジュールを抜粋したものです。実際のリポジトリではさらにファイルが存在する場合があります。）

## テスト・開発メモ
- OpenAI 呼び出しは network 依存なので unit test では _call_openai_api を patch してテストしてください。
- news_collector は SSRF 対策・最大受信サイズ・XML の安全パーサ（defusedxml）を使用しています。外部 URL を使うシナリオのテストではローカルのモックサーバを利用してください。
- DuckDB の executemany はバージョン依存の挙動があるため、コード中で空リスト対策が行われています（空の executemany を避ける等）。

## ログ
LOG_LEVEL 環境変数でログレベルを制御できます（デフォルト INFO）。各モジュールは適切に logger を使用しており、重要な操作（ETL の取得/保存、API エラー、品質チェック結果など）を記録します。

---

この README はコードベースの使用開始と開発を支援する概要ドキュメントです。より詳細な設計や運用ルール（データベーススキーマ詳細、監査テーブル仕様、StrategyModel.md / DataPlatform.md の参照）は別資料に記載されています。質問や追加説明が必要であれば教えてください。