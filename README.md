# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定トレース）など、アルゴリズムトレードとリサーチに必要な共通機能群を提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local からの自動読み込み（CWD に依存しないプロジェクトルート検出）
  - 必須設定の明示（Settings クラス）
- データ取得 / ETL（J-Quants 統合）
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - ETL の実行結果（ETLResult）で品質問題やエラーを収集
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合チェック
  - QualityIssue を返す設計で Fail-Fast せず問題を一覧化
- ニュース収集 / NLP
  - RSS 収集（SSRF 対策、トラッキング除去、受信上限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（ai_scores 書き込み）
  - レート制限・リトライ・レスポンス検証を含む堅牢な呼び出し
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジームを判定
  - レジーム結果を market_regime テーブルへ冪等書込
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止
- リサーチ支援
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- 汎用ユーティリティ
  - クロスセクション Z スコア正規化など（data.stats）

---

## 前提・依存

- Python 3.10 以上（型ヒントに `|` を使用）
- 主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由 API（J-Quants, OpenAI）を使用する機能は各種 API キーが必要

requirements.txt が無い場合は上記をインストールしてください。例:

pip install duckdb openai defusedxml

（追加で packaging / logging 等の標準ライブラリを使用）

---

## 環境変数（必須 / 推奨）

プロジェクトでは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みします。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主な環境変数（README 用の最小セット）:

- JQUANTS_REFRESH_TOKEN  ← J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      ← kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL      ← kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        ← Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       ← Slack チャンネル ID（必須）
- DUCKDB_PATH            ← DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            ← 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV            ← environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              ← DEBUG/INFO/...（デフォルト INFO）
- OPENAI_API_KEY         ← OpenAI API キー（AI 機能を使う場合に必須）

例（.env）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （その他、ロギングやデプロイ先に応じた追加ライブラリ）
4. プロジェクトルートに .env を作成（上記参照）
5. DuckDB ファイルディレクトリがない場合は作成（設定で指定したパスの親ディレクトリ）

---

## 使い方（代表的なサンプル）

以下は Python REPL やスクリプトから呼び出す際の例です。

- ETL（デイリー ETL を実行）

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(__import__('kabusys').config.settings.duckdb_path))  # または str(Path("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュース NLP スコアリング（OpenAI キーが必要）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で指定
print(f"scored {count} symbols")

- 市場レジーム判定（OpenAI キーが必要）

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ保存される

- 監査ログ DB 初期化（監査専用 DB）

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # テーブル定義とインデックスを作成

- ファクター計算 / リサーチ関数

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))

注: 上記関数の多くは DuckDB 内のテーブル（prices_daily, raw_news, raw_financials, market_calendar 等）を参照します。事前に ETL でデータを投入してください。

---

## 実運用上の注意

- Look-ahead バイアス対策
  - すべての AI / 指標計算は内部で `target_date` を明示的に受け取り、datetime.today() 等に依存しない設計です。バックテスト/トレーニング時のバイアスを防ぐため、必ず過去のデータのみを使うようにしてください。
- 冪等性
  - ETL や保存関数は基本的に冪等（ON CONFLICT / DELETE→INSERT 等）を意識して設計されています。
- API キー
  - OpenAI / J-Quants はレート制限や課金が発生します。テスト実行時は少量で確認してください。
- 自動 .env ロード
  - パッケージ初期化時にプロジェクトルートを探索して `.env` / `.env.local` を読み込みます。テストで自動ロードを抑制したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下はソースコードの主要なファイル群（抜粋）です。実際のリポジトリではさらに補助ファイルやテスト等が存在する場合があります。

src/kabusys/
- __init__.py
- config.py                       ← 環境変数と Settings 管理
- ai/
  - __init__.py
  - news_nlp.py                    ← ニュースの LLM ベースセンチメント付与（score_news）
  - regime_detector.py             ← 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py              ← J-Quants API クライアント（fetch / save）
  - pipeline.py                    ← ETL パイプライン（run_daily_etl 等）
  - etl.py                         ← ETLResult 再エクスポート
  - news_collector.py              ← RSS 収集と前処理
  - calendar_management.py         ← 市場カレンダーの判定 / 更新ジョブ
  - stats.py                       ← 統計ユーティリティ（zscore_normalize）
  - quality.py                     ← データ品質チェック群
  - audit.py                       ← 監査テーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py             ← Momentum / Value / Volatility 計算
  - feature_exploration.py         ← 将来リターン / IC / summary
- monitoring/                       ← （モニタリング/アラート関連の想定場所）
- strategy/                         ← （戦略生成・ポートフォリオ構築の想定場所）
- execution/                        ← （ブローカー連携・発注ロジックの想定場所）

---

## 開発者向けメモ

- テストと CI
  - 環境依存性（.env 自動ロード）を制御するために `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用できます。
  - OpenAI / J-Quants 呼び出しは patch / mock しやすいように内部で _call_openai_api / _request 等を分離しています。
- エラーハンドリング
  - ネットワーク系呼び出しはリトライ・バックオフ実装あり。また、AI レスポンスのパース失敗時はフェイルセーフ（0.0 など）で継続する設計が多いです。
- 型・互換性
  - DuckDB のバージョン差異（executemany の挙動など）を踏まえた実装注意点がコメントに残されています。

---

もし README に追加したい具体的な利用例（CLI スクリプト、Docker、CI 設定、.env.example のテンプレートなど）があれば教えてください。必要に応じて追記・テンプレート作成を行います。