# KabuSys

日本株自動売買システム用ライブラリ / プラットフォーム（軽量モジュール群）

このリポジトリは、データ取得・ETL、データ品質チェック、ニュース収集とAIによるニュース評定、
市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを
まとめた Python モジュール群です。バックテストや自動売買の各層で再利用できるユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（日付参照を外部入力化）
- DuckDB を中心としたローカルデータストア
- J-Quants API 経由の差分ETL（レート制限・リトライ対応）
- OpenAI（gpt-4o-mini）を使ったニュース NLP / マクロセンチメント（フェイルセーフ実装）
- 冪等性を重視した DB 書き込み（ON CONFLICT / DELETE→INSERT 等）
- 外部サービスへの接続情報は環境変数もしくは .env で管理

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境変数の設定
  - ETL の実行例
  - ニューススコアリング（AI）
  - 市場レジーム判定（AI）
  - 監査 DB の初期化
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株運用に必要なデータ基盤・リサーチ・AI 補助機能・監査ログを
  コンポーネント化して提供します。
- 主な用途：日次 ETL（株価・財務・カレンダー）、ニュース収集・センチメント評価、
  ファクター計算、監査ログ生成、マーケットレジーム判定、データ品質チェック等。

---

機能一覧
- data.jquants_client
  - J-Quants API からの株価・財務・カレンダーのフェッチ、DuckDB への冪等保存
  - レートリミット制御、リトライロジック（401 の自動リフレッシュ含む）
- data.pipeline
  - 日次 ETL 実行（calendar → prices → financials → 品質チェック）
  - ETL 結果を ETLResult として返却
- data.quality
  - 欠損・重複・スパイク・日付不整合などの品質チェック、QualityIssue 定義
- data.news_collector
  - RSS フィード収集、前処理、SSRF 対策、raw_news への冪等保存
- ai.news_nlp
  - 銘柄ごとにニュースをまとめて LLM（gpt-4o-mini）に投げ、銘柄センチメントを ai_scores に保存
- ai.regime_detector
  - ETF 1321（Nikkei 225 連動）の MA200 乖離とマクロニュースセンチメントを合成し
    日次で market_regime テーブルへ書き込み（'bull'/'neutral'/'bear'）
- research.*
  - ファクター計算（momentum / volatility / value）、forward returns、IC、統計サマリ等
- data.audit
  - シグナル→発注→約定までの監査テーブル定義・初期化ユーティリティ
- data.calendar_management
  - market_calendar を使った営業日判定・前後営業日検索・夜間更新ジョブ
- config
  - .env 自動ローディング（プロジェクトルート検出）、Settings オブジェクトで環境変数を参照

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```bash
   git clone <this-repo>
   cd <this-repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 依存一覧はプロジェクトの pyproject.toml / requirements.txt を参照してください。
   - 代表的な依存：
     - duckdb
     - openai
     - defusedxml
     - その他（logging, urllib は標準ライブラリ）
   例:
   ```bash
   pip install duckdb openai defusedxml
   # 開発用には editable install
   pip install -e .
   ```

4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（またはよく使う）環境変数一覧
- JQUANTS_REFRESH_TOKEN   : J-Quants のリフレッシュトークン（get_id_token に利用）
- OPENAI_API_KEY          : OpenAI API キー（ai.news_nlp / ai.regime_detector のデフォルト）
- KABU_API_PASSWORD       : kabuステーション API のパスワード（実行層で使用）
- SLACK_BOT_TOKEN         : Slack 通知に使用
- SLACK_CHANNEL_ID        : Slack 通知先チャンネル
- DUCKDB_PATH             : デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH             : 監視用 sqlite パス（例: data/monitoring.db）
- KABUSYS_ENV             : environment ('development' / 'paper_trading' / 'live')
- LOG_LEVEL               : ログレベル（DEBUG/INFO/...）

例 .env（最低限の例）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

使い方（主要ユースケース）

事前準備：
- DuckDB データベースのファイルパス（デフォルト data/kabusys.duckdb）が保存先になります。
- OpenAI キーや J-Quants トークンは環境変数か各関数の api_key/id_token 引数で渡せます。

1) ETL（日次 ETL）の実行例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。
- id_token を明示的に渡すことも可能（テスト用など）。

2) ニューススコアリング（AI）
- OpenAI API キーを環境変数 OPENAI_API_KEY にセットするか、api_key 引数で渡します。
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```
- raw_news / news_symbols / ai_scores テーブルを前提に処理します。
- 空のニュースや API エラー時はフェイルセーフでスキップします。

3) 市場レジーム判定（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```
- ETF 1321 の MA200 乖離とマクロニュースセンチメント（LLM）を合成して market_regime テーブルへ保存します。

4) 監査 DB の初期化
- 発注 / 約定の監査テーブルを作成するユーティリティ。
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以後 conn を用いて監査テーブルへ挿入やクエリが可能
```

5) カレンダー/営業日ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点
- 各モジュールは DB スキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar, など）を前提に実装されています。DB スキーマの初期化は別途スキーマ定義モジュールやマイグレーションで行ってください（このコードベースにはスキーマ初期化の全体版は含まれていませんが、audit 用の init_audit_schema 等は提供しています）。
- OpenAI の呼び出しは JSON Mode を利用して厳密な JSON 出力を期待しています。API エラーや不正レスポンスがあってもフェイルセーフ設計（0.0 やスキップ）で継続します。

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・.env 自動ロード / Settings
    - ai/
      - __init__.py
      - news_nlp.py                  # ニュースNLP スコアリング（gpt-4o-mini）
      - regime_detector.py           # 市場レジーム判定（MA200+マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント（fetch/save）
      - pipeline.py                  # ETL パイプライン / run_daily_etl 等
      - etl.py                       # ETLResult の公開
      - news_collector.py            # RSS 収集・前処理・保存
      - calendar_management.py       # market_calendar 管理 / 営業日判定
      - quality.py                   # データ品質チェック
      - audit.py                     # 監査ログテーブル定義・初期化
      - stats.py                     # 汎用統計（zscore_normalize）
    - research/
      - __init__.py
      - factor_research.py           # モメンタム / バリュー / ボラティリティ
      - feature_exploration.py       # forward returns / IC / summary / rank
    - research/...                     # その他リサーチ補助モジュール

この README はコードベースの主要な機能と利用方法を簡潔にまとめたものです。実運用や本番環境での利用時は下記点に注意してください：
- API キーやパスワード等の秘匿情報は適切に管理する（環境変数・シークレット管理を推奨）
- 実取引を行う際はオーダー発行部分（broker 接続やリスク管理）を別途安全に実装し、本ライブラリの監査ログ等と連携してください
- OpenAI 等の外部 API 呼び出しにはコストとレート制限が伴います。バッチ化・キャッシュを検討してください

必要であれば、README に含めるサンプル DB スキーマ、より具体的な起動スクリプト、または CI / テスト手順の追記も作成します。どの情報を追加したいか教えてください。