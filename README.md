# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
J-Quants や RSS / OpenAI 等の外部データを取り込み、ETL、データ品質チェック、ファクター計算、ニュースNLP、監査ログなどを通じて運用・研究・発注の各層を支援します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を用いたオンディスク ETL / 分析
- 冪等性（ON CONFLICT / トランザクション）を重視した保存処理
- 外部 API（J-Quants / OpenAI / RSS）への堅牢な呼び出し（レート制御・リトライ・フェイルセーフ）

---

## 機能一覧
- 環境設定管理（.env 自動読み込み / Settings ラッパー）
- J-Quants API クライアント（株価 / 財務 / マーケットカレンダーの取得・保存）
- ETL パイプライン（日次 ETL: カレンダー→株価→財務→品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定・次/前営業日取得・夜間更新ジョブ）
- ニュース収集（RSS → raw_news 保存、SSRF 対策・正規化）
- ニュースNLP（OpenAI を用いた銘柄ごとのセンチメント集計 → ai_scores 保存）
- 市場レジーム判定（ETF 1321 の MA + マクロニュースセンチメント合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal_events / order_requests / executions）スキーマ生成・初期化

---

## 前提（Requirements）
- Python 3.9+（型注釈で Union 複数形を使用しているため 3.10 推奨）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS ソース 等）
- J-Quants / OpenAI の API キー（環境変数または .env）

（実プロジェクトでは requirements.txt / pyproject.toml に依存関係を明記してください）

---

## セットアップ手順

1. リポジトリをクローン・仮想環境作成
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存パッケージをインストール
   (実プロジェクトの requirements.txt / pyproject.toml に合わせてください)
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（package 起動時）。
   - 例: `.env` に以下を設定
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN（必須: J-Quants リフレッシュトークン）
   - OPENAI_API_KEY（OpenAI 呼び出しで未指定時に使用）
   - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API 用）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
   - DUCKDB_PATH, SQLITE_PATH（データベースパス）
   - PID_FILE_PATH, KILL_FLAG_PATH（監視）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG/INFO/...）

4. データディレクトリ作成
   ```
   mkdir -p data
   ```

5. DuckDB（監査DB）初期化（例）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   conn.close()
   ```
   または既存接続にスキーマを追加:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要な API と例）

基本的に DuckDB 接続を作成し（path は settings.duckdb_path 参照）、各モジュールの関数を呼びます。

共通: DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を走らせる
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを取得して保存（ai_scores へ）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すことも可能（渡さない場合は OPENAI_API_KEY を参照）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書込み銘柄数: {n_written}")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

5) ニュース RSS 取得（単独取得。DB 保存ロジックは news_collector に実装）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"])
```

6) J-Quants 直接呼び出し（開発・デバッグ用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

7) 監査ログ（初期化済み DB に対する使用）
- 監査用テーブルは init_audit_schema / init_audit_db で作成します。
- 戦略レイヤーは signal_events / order_requests / executions に記録する想定です（本 README では発注実装は含まれません）。

---

## 設計上の注意点・運用メモ
- Look-ahead bias に配慮して、ターゲット日ベースのウィンドウ計算や DB クエリで date < target_date のような排他条件を用いています。バックテスト等で使用する際は取り扱いに注意してください。
- OpenAI 呼び出しは JSON Mode を想定し、レスポンス検証を慎重に行っています。API 失敗時はゼロやスキップでフォールバックする設計です（フェイルセーフ）。
- J-Quants API のレート制限をモジュール内で制御しています（120 req/min）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。CI / テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかにしてください。LOG_LEVEL は標準的なログレベルを使用します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                : 環境変数・設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py            : ニュースセンチメント → ai_scores
  - regime_detector.py     : 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント（取得・保存）
  - pipeline.py            : 日次 ETL（run_daily_etl など）
  - etl.py                 : ETLResult の公開
  - calendar_management.py : マーケットカレンダー管理 / 更新ジョブ
  - news_collector.py      : RSS 収集・前処理
  - stats.py               : zscore_normalize 等の統計ユーティリティ
  - quality.py             : データ品質チェック（QualityIssue）
  - audit.py               : 監査ログスキーマ初期化（signal / order / execution）
- research/
  - __init__.py
  - factor_research.py     : momentum/volatility/value 計算
  - feature_exploration.py : forward returns / IC / summary utilities
- research/... (その他 helper)

（実際のリポジトリはさらにテスト、サンプルスクリプト、pyproject.toml 等を含むことを想定しています）

---

## トラブルシューティング
- .env が読み込まれない
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行われます。該当ファイルがない場合は自動読み込みをスキップします。
  - 自動読み込みを無効化しているか確認（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- OpenAI / J-Quants API 呼び出しでタイムアウト・エラー
  - ライブラリはリトライとバックオフを行います。キーやネットワークに問題がある場合はログを確認してください。
- DuckDB に対する権限・パスの問題
  - settings.duckdb_path を確認し、親ディレクトリが存在するか（setup 手順で data ディレクトリを作成）を確認してください。

---

## ライセンス / 責任
- 本コードはサンプル実装/ライブラリとして提供されています。実際の自動売買運用では十分なテスト、モニタリング、リスク管理を実施してください。金融取引に伴う損失について作者は責任を負いません。

---

必要であれば、セットアップ用の requirements.txt、例の .env.example、簡易 CLI スクリプト（etl_runner、news_scanner 等）の雛形を追加で作成します。どの形式で README を拡張したいか教えてください。