# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（オーディット）などを含みます。

---

## 主要な特徴（概要）

- J-Quants API 経由で株価・財務・マーケットカレンダーを差分取得・保存（DuckDB）
- ニュース収集（RSS）と前処理 → OpenAI による銘柄別センチメントスコア化（gpt-4o-mini, JSON mode）
- 市場レジーム判定（ETF 1321 の 200日MA乖離 + マクロニュースセンチメントの重み付け）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレース）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Zスコア正規化）
- 環境変数 / .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`）

---

## 機能一覧（サブモジュール）

- kabusys.config
  - 環境変数の自動読み込み／管理、必須キー取得
- kabusys.data
  - jquants_client: J-Quants API とのやり取り（取得・保存・認証・レート制御）
  - pipeline: run_daily_etl を含む ETL パイプライン／ETLResult
  - news_collector: RSS 収集・前処理・保存
  - calendar_management: 市場カレンダー管理・営業日ロジック
  - quality: データ品質チェック
  - audit: 監査ログスキーマ初期化、監査用 DB 作成ユーティリティ
  - stats: 汎用統計（Zスコア正規化）
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でスコア化 → ai_scores に保存
  - regime_detector.score_regime: ETF とマクロニュースを組み合わせて市場レジームを判定 → market_regime に保存
- kabusys.research
  - factor_research: momentum / volatility / value 計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## 必要要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで HTTP は urllib を使用（追加の HTTP ライブラリは不要）

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。例として:

pip install duckdb openai defusedxml

（パッケージ名は環境に応じて適宜）

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ移動

2. Python 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそれを使用）

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env` / `.env.local` を置くと、パッケージインポート時に自動で読み込まれます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuAPI のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に使う）
   - 任意:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）

5. データディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（簡易ガイド）

以下は Python REPL やスクリプトから利用する例です。

基本: DuckDB 接続を渡して各関数を呼ぶ流れになります。

1) DuckDB 接続を用意する

from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ETL は市場カレンダー → 株価 → 財務 → 品質チェックの順で実行します。
- id_token を直接渡すことも可能（J-Quants 認証の注入でテスト容易性向上）。

3) ニュースのスコアリング（OpenAI を利用）

from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡さない場合は OPENAI_API_KEY 環境変数を参照

score_news は ai_scores テーブルへ書き込みます。

4) 市場レジーム判定（ETF 1321 に基づく）

from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 同様に OPENAI_API_KEY を参照

5) 監査ログスキーマの初期化（監査用 DB 作成）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査用 DuckDB 接続（UTC タイムゾーン設定済み）

6) 研究 / ファクター計算の例

from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))

---

## .env の自動読み込みについて

- パッケージ import 時にプロジェクトルート（現在ファイルの親階層で .git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

---

## 開発・テスト上の注意点

- OpenAI や外部 API 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 スコア・処理スキップ等）を備えていますが、ユニットテストでは外部呼び出しをモックすることを推奨します。実装は各モジュールで _call_openai_api のモックを想定しています。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、空チェックを行っています。実運用時は DuckDB のバージョン互換性に注意してください。
- コードは Look-ahead bias を防ぐ設計（date < target_date の条件や target_date 引数による決定）になっています。バックテストでの日付取り扱いに注意してください。

---

## ディレクトリ構成（抜粋）

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
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（プロジェクトルートには pyproject.toml や .git/、.env.example 等がある想定です）

---

## よくある質問 / トラブルシューティング

- Q: OpenAI キーが見つからないと言われる
  - A: score_news / score_regime の api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定してください。

- Q: .env が読み込まれない
  - A: パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動探索して .env を読み込みます。テスト中や別パスで動かす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから独自に環境変数をセットしてください。

- Q: DuckDB のファイルに書き込みできない
  - A: settings.duckdb_path のディレクトリが存在するか、プロセスに書き込み権限があるか確認してください。data ディレクトリを作成してください。

---

必要があれば、README に入れるサンプル .env.example、CI 用の設定や運用手順（cron/バッチ実行例）、具体的な SQL スキーマ説明や API レート制御の運用方針なども追記できます。どの部分を詳しくしたいか教えてください。