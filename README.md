KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株のデータ取得（ETL）、データ品質チェック、ニュース NLP（LLM によるセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などの機能を備えたライブラリ群です。本リポジトリは主にデータプラットフォーム周り（DuckDB を用いた永続化・ETL）および研究（ファクター計算）・AI（ニューススコアリング / レジーム判定）に重心を置いて実装されています。

特徴（機能一覧）
----------------
- 環境設定管理
  - .env / .env.local の自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数取得時に明示的エラー

- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー等をページネーション対応で取得
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ、取得時刻（fetched_at）記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
  - 品質チェック: 欠損、スパイク、重複、日付不整合などを検出して QualityIssue を返す

- ニュース収集 / 前処理
  - RSS フィード収集、URL 正規化、SSRF 対策、XML 脆弱性対策（defusedxml 使用）
  - raw_news / news_symbols などとの紐付け（冪等保存）

- ニュース NLP（LLM）
  - gpt-4o-mini を想定した JSON モードでのバッチ評価
  - 銘柄毎のセンチメント ai_score を ai_scores テーブルへ保存
  - リトライ、レスポンスバリデーション、スコアクリップ

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離 + マクロニュースセンチメントを合成して 'bull'/'neutral'/'bear' を判定
  - OpenAI API 呼び出しはフェイルセーフ（失敗時は macro_sentiment=0.0）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の SQL と Python の組合せ）
  - 将来リターン計算、IC（Spearman ランク相関）、Z スコア正規化等のユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）
  - UUID を用いたトレーサビリティ、UTC タイムスタンプ運用

セットアップ
---------
必要条件
- Python 3.10 以上（typing の | Union を使用しているため）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（LLM を使用する機能を使う場合）
- defusedxml（RSS パースの安全化）

推奨インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 編集可能インストール（開発時）
   - pip install -e .

環境変数（主なもの）
-------------------
以下は本コードベースで参照される主な環境変数です（.env/.env.local に設定可能）。

必須（使用する機能に応じて必須）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（fetch API 用）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector が必要とする）
- KABU_API_PASSWORD — kabu API パスワード（kabu 関連機能）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能使用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイルパス
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値

.env 自動読み込み
- パッケージ起点で .env / .env.local を自動読み込みします（OS 環境変数が優先）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

基本的な使い方（コード例）
-----------------------

1) DuckDB 接続を用意して ETL を実行する

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニューススコアリング（LLM）を実行する

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")

※ OpenAI API キーは環境変数 OPENAI_API_KEY で設定するか、score_news の引数 api_key に渡してください。

3) 市場レジーム判定を実行する

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログスキーマの初期化

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

運用上の注意
------------
- OpenAI / J-Quants を呼ぶ処理は外部 API に依存するため、API キー・レート制限・エラー時のフォールバックを考慮してください。
- ニュース収集は RSS ソースの信頼性・サイズに注意（MAX_RESPONSE_BYTES による制限あり）。
- ETL/研究系関数はルックアヘッドバイアスを避ける設計になっていますが、バックテストで使う場合はデータ取得タイミングに注意してください。
- DuckDB の executemany に対する制約（バージョンに依存）を考慮して一部処理で空リストの挙動に注意しています。

ディレクトリ構成
---------------
以下は主要なファイル・モジュールの概観（src/kabusys 以下）。

src/kabusys/
- __init__.py
- config.py                          -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                       -- ニュースの LLM スコアリング
  - regime_detector.py                -- マクロ + ETF を組合せた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                 -- J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
  - etl.py                            -- ETLResult エクスポート
  - quality.py                        -- データ品質チェック
  - news_collector.py                 -- RSS 収集・前処理
  - calendar_management.py            -- マーケットカレンダー管理 / 営業日判定
  - stats.py                          -- zscore_normalize 等の統計ユーティリティ
  - audit.py                          -- 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py                -- モメンタム / ボラ / バリューなど
  - feature_exploration.py            -- 将来リターン calc/ic/factor_summary 等
- research/*（他ユーティリティ）
- その他: strategy / execution / monitoring（パッケージ公開対象に含めるが、上記は実装の一部）

ライセンス・貢献
----------------
本コードベースのライセンス情報・コントリビューションガイドはリポジトリルートの LICENSE / CONTRIBUTING 等を参照してください（ここには含まれていません）。

FAQ / トラブルシューティング
---------------------------
Q: OpenAI のレスポンスが期待どおりの JSON で返らない場合は？
A: レスポンスを厳密に検証し、パースに失敗した場合はフェイルセーフでスコア 0.0 を採用する実装です。ログを確認してプロンプトやモデル挙動を調整してください。

Q: .env が読み込まれない
A: パッケージは import 時にプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB への書き込みでエラーが出る
A: 特に executemany に空パラメータを渡すと DuckDB のバージョン依存でエラーになる場合があります。本実装はその点に配慮しており、空のときは実行しないようにしています。エラーログ（例外トレース）を確認してください。

最後に
-------
この README はコードベースの主要機能と利用手順をまとめた概要です。詳細な API 仕様や追加のユーティリティは各モジュールの docstring / ソースコメントを参照してください。追加で欲しい節（例: 詳細な .env.example、CI 設定、デプロイ手順など）があれば教えてください。