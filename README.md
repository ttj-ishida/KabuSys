# KabuSys

日本株向けデータプラットフォーム & 自動売買支援ライブラリ（KabuSys）。  
J-Quants / DuckDB を用いたデータ ETL、ニュース NLP（LLM）による銘柄センチメント評価、マーケットレジーム判定、監査ログ（オーダー/約定）スキーマなどを含むライブラリ群です。

主な設計方針：
- ルックアヘッドバイアスを避けるため、内部で date.today() を直接参照しない設計（呼び出し側が基準日を渡す）。
- ETL / 保存処理は冪等性（ON CONFLICT）を重視。
- 外部 API 呼び出しに対してリトライ・レート制御・フェイルセーフを備える。
- DuckDB を中心とした軽量ローカルデータベースでの処理。

バージョン: 0.1.0

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価（日足）、財務、上場銘柄情報、JPX マーケットカレンダーの取得
  - 差分取得（バックフィル対応）、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の統合エントリポイント run_daily_etl
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースセンチメントの重み合成で日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義、初期化ユーティリティ（init_audit_schema / init_audit_db）
- 共通ユーティリティ
  - 環境設定管理（.env 自動読み込み）、ログレベル/環境フラグ、DB パス管理
  - 統計ユーティリティ（zscore_normalize） etc.

---

## 要求環境・依存

- Python >= 3.10（PEP 604 の型記法（|）等を使用）
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- 推奨: pipenv/venv を用いた仮想環境

依存インストール例:
pip install duckdb openai defusedxml

プロジェクトがパッケージ化されている場合:
pip install -e .

（実際の requirements.txt は本リポジトリに依存関係ファイルがある場合はそちらを利用してください）

---

## 環境変数（主要）

KabuSys は環境変数または .env ファイルから設定を読み込みます（自動ロード有効）。主要なキー：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で参照）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に必要（任意）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）

自動 .env 読み込みについて：
- パッケージ内の config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、
  .env → .env.local の順に読み込みます（OS 環境変数を優先）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時など）。

.envの例（.env.example を参照してください）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンする
   - git clone <repo_url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt があれば）
   - または主要パッケージを個別に: pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参照）
   - または CI / 実行環境の環境変数に設定
5. DuckDB データディレクトリを作成（必要なら）
   - mkdir -p data
6. （任意）監査 DB 初期化:
   - python で init_audit_db を呼び出す（下記参照）

---

## 使い方（よく使う API と例）

以下は簡単な Python スクリプト例です。日付は必ず呼び出し側が渡す（ルックアヘッド防止）。

- 共通設定の参照:
from kabusys.config import settings
print(settings.duckdb_path, settings.env)

- DuckDB 接続と ETL（日次 ETL の実行）:
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコア（OpenAI を用いた銘柄センチメント）:
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は duckdb 接続、api_key は None の場合 OPENAI_API_KEY を参照
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")

- 市場レジーム判定:
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI APIキーは環境変数でも指定可

- 監査ログ DB 初期化（別 DB 推奨）:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます

- ニュース収集（RSS の取得。DB への保存ロジックは別途実装される想定）:
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"])

注意点：
- OpenAI 呼び出しはネットワークエラーやレート制限に対してリトライやフェイルセーフを備えていますが、APIキーは必須です。
- run_daily_etl 等は処理中のエラーを result.errors に収集し続行します。戻り値 ETLResult を確認して運用上の判断を行ってください。

---

## ディレクトリ構成（要約）

src/kabusys/
- __init__.py
- config.py                            — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py                         — ニュースセンチメント（score_news）
  - regime_detector.py                  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py              — 市場カレンダー操作・判定ユーティリティ
  - pipeline.py                         — ETL 全体制御（run_daily_etl等）
  - etl.py                              — ETLResult 再エクスポート
  - jquants_client.py                   — J-Quants API クライアント & 保存ロジック
  - news_collector.py                   — RSS 取得・前処理・SSRF 対策
  - quality.py                          — データ品質チェック
  - stats.py                            — 統計ユーティリティ（zscore_normalize）
  - audit.py                            — 監査ログ（スキーマ作成 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py                  — Momentum/Volatility/Value の計算
  - feature_exploration.py              — 将来リターン/IC/統計サマリー 等
- research には zscore_normalize の再エクスポートあり

ドメイン別に分割されたモジュール群になっており、ETL・データ品質・研究・AI評価・監査ログが独立した責務で実装されています。

---

## 運用上の注意

- 本ライブラリは実稼働（特に発注機能）に接続する前に必ずセキュリティ（APIキー管理）、バックテスト、ステージング環境での検証を行ってください。
- KABUSYS_ENV に "live" を設定すると実稼働フラグに基づく挙動切り替えを期待するコードが利用できます。運用前に全ての安全チェックを実施してください。
- DuckDB のバージョン差異（executemany の挙動など）に注意してください（コード中にも互換性ワークアラウンドあり）。
- OpenAI / J-Quants などサードパーティ API のレート上限・料金に注意して運用してください。

---

ご要望があれば、README に以下を追加できます：
- サンプル .env.example（テンプレート）
- CI/CD（GitHub Actions）用のワークフローテンプレート
- より詳細な API 使用例（各モジュールごと）
- Docker / コンテナ化手順

必要に応じて追記・調整します。