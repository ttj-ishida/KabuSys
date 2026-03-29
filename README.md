# KabuSys

日本株のデータ基盤 / リサーチ / 自動売買のための共通ライブラリ群です。  
ETL による J-Quants データ収集、ニュース収集・NLP、ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要サブシステムを含むモジュール群です。

- data: J-Quants からのデータ取得（株価・財務・カレンダー）、ETL パイプライン、データ品質チェック、ニュース収集、監査ログ（トレーサビリティ）等
- ai: ニュースのセンチメント分析（OpenAI を用いる）および市場レジーム判定
- research: ファクター計算・特徴量探索・統計ユーティリティ
- config: 環境変数 / .env 管理
- その他: 実行・監視・戦略層との連携を想定した補助モジュール群

設計上の特徴:
- DuckDB を主要なローカル DB として利用（データ永続化）
- Look-ahead バイアスを防ぐ設計（API 呼び出しや日付計算で datetime.today() を直接参照しない）
- J-Quants / OpenAI API 呼び出しに堅牢なリトライ・レート制御
- ETL は差分更新・バックフィル・品質チェックを備える
- ニュース収集は SSRF 等のセキュリティ対策を実装

---

## 機能一覧

主な機能（抜粋）:

- ETL（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー・株価日足・財務データの差分取得と保存、品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
  - ETLResult: 実行結果オブジェクト

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_* / save_* 系関数（daily_quotes, financial_statements, market_calendar, listed_info 等）
  - レートリミット・リトライ・トークン自動リフレッシュ対応

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・ID 生成・前処理・DB への冪等保存
  - SSRF / gzip / サイズ制限 / トラッキングパラメータ除去 等の保護

- データ品質チェック（kabusys.data.quality）
  - 欠損検出 / スパイク検出 / 重複検出 / 日付整合性チェック
  - QualityIssue による詳細レポート

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルとインデックス定義
  - init_audit_db / init_audit_schema による初期化（UTC タイムスタンプ）

- AI ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window / score_news: 指定ウィンドウのニュースを LLM（gpt-4o-mini）に送り、銘柄別センチメントを ai_scores に書き込む
  - バッチ処理・検証・スコアクリップ（±1.0）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で regime（bull/neutral/bear）判定

- リサーチ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・IC 計算

---

## 必要要件

最低限の Python パッケージ（実行環境により異なります）。主に以下が必要になります（一例）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## 環境変数

設定は .env（プロジェクトルート）および .env.local を自動的にロードします（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必須。または関数引数で渡す）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルトあり:

- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）（デフォルト: INFO）

注意: config.Settings の property が必要な変数を _require() でチェックします。README に .env.example を用意し、実行前に必須キーを設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または minimal:
   - pip install duckdb openai defusedxml

4. プロジェクトルートに .env を作成（.env.example を参照）

5. DuckDB DB ファイルの準備（必要なら）
   - デフォルトは data/kabusys.duckdb（settings.duckdb_path）。ディレクトリは自動作成してください。

---

## 初期化 / 使い方（例）

以下は基本的な Python API 呼び出し例です。プロセスはアプリケーションから直接呼ぶことを想定しています。

- ETL の実行（run_daily_etl）:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- 監査ログ DB 初期化（独立 DB を作る場合）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY もしくは引数で渡す）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に API キーを渡すことも可能
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込み銘柄数:", n_written)

- 市場レジーム判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)

注意点:
- score_news / score_regime は内部で OpenAI クライアントを作成します。API キーを渡すか、環境変数 OPENAI_API_KEY を設定してください。
- AI 書き込み先のテーブル（ai_scores / market_regime 等）が存在することを確認してください（スキーマ初期化が必要な場合は適宜スキーマ作成処理を呼んでください）。

---

## 実装上の注記・設計方針

- Look-ahead バイアス対策: 日付クエリやウィンドウ指定は target_date を明示して呼び出すことを前提にしており、モジュール内部で datetime.today() 等を参照する実装は避けられています。
- 冪等性: save_* 関数は ON CONFLICT DO UPDATE（または相当手法）で冪等保存を行います。
- セキュリティ: ニュース収集は SSRF 対策、XML パースは defusedxml を利用、RSS レスポンスサイズ制限などを実装しています。
- API 呼び出し: J-Quants は固定間隔レートリミッタ、OpenAI 呼び出しはリトライとエラーハンドリングを備えています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - etl.py
  - news_collector.py
  - quality.py
  - stats.py
  - calendar_management.py
  - audit.py
  - pipeline.py (ETLResult エクスポート)
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- その他（strategy / execution / monitoring を想定したパッケージ配下の公開）

（README の末尾に小さなファイル一覧を置いていますが、実際のリポジトリではパッケージ全体を参照してください）

---

## 開発 / テスト

- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動ロードが無効になり、ユニットテストで環境を分離できます。
- OpenAI 呼び出し箇所（news_nlp._call_openai_api / regime_detector._call_openai_api）はテスト時に patch / mock しやすいよう分離しています。

---

## 補足

- 本 README はコードベースから抽出した概要ドキュメントです。より具体的な実運用（戦略の実装、発注フロー、監視）については別途ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照してください。
- 質問や追加の使用例が必要であれば、どの機能についてのドキュメントが欲しいか教えてください。