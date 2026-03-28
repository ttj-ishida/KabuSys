KabuSys — 日本株自動売買プラットフォーム（README）
====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買基盤の一部コンポーネント群です。本リポジトリには以下を実装しています。

- J-Quants API を使った株価・財務・マーケットカレンダーの ETL パイプライン
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースの NLP スコアリング（ai_scores）と市場レジーム判定
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order / execution）用の DuckDB スキーマ初期化ユーティリティ

特徴（主な機能）
----------------
- データ取得（J-Quants）: 差分取得・ページネーション・リトライ・レート制御を備えたクライアント
- ETL パイプライン: 日次 ETL（calendar / prices / financials）と品質チェック
- ニュース収集: RSS 収集・前処理・SSRF/サイズ/トラッキングパラメータ対策
- ニュース NLP: OpenAI を用いた銘柄ごとのセンチメントスコアリング（バッチ・リトライ実装）
- レジーム判定: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジームを判定
- 研究ユーティリティ: ファクター計算（momentum/volatility/value）や forward returns / IC / summary
- データ品質チェック: 複数チェックを集約して問題レポートを返す
- 監査ログ: シグナル→発注→約定までトレース可能なテーブル定義と初期化

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子を使用しているため）
- DuckDB（Python パッケージとしてインストール）
- OpenAI Python SDK（gpt-4o-mini 呼び出し用）
- defusedxml（RSS パースの安全対策）

例: 仮想環境の作成と依存インストール
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   pip install duckdb openai defusedxml

   ※プロジェクト配布で requirements.txt / pyproject.toml があればそちらを使用してください。

環境変数
- 設定は .env / .env.local または OS 環境変数で行います。自動読み込みはパッケージ起点（.git または pyproject.toml の場所）から行われ、優先順位は:
  OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（必須／推奨）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（ai モジュールを使う場合必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL      : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID       : Slack チャンネル ID
- DUCKDB_PATH            : デフォルトの DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : environment (development | paper_trading | live)
- LOG_LEVEL              : ログレベル (DEBUG/INFO/...)


使い方（実例）
----------------

基本的な DuckDB 接続
- Python から直接 DuckDB 接続を作成して各 API を呼び出します。設定は kabusys.config.settings で読み取れます。

例: 日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB 接続（ファイル path は settings.duckdb_path を使う）
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

例: ニュース NLP スコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境にある場合、api_key 引数は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

例: 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

例: 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db
# data/audit.duckdb を作成して監査スキーマを初期化
conn = init_audit_db("data/audit.duckdb")
```

研究（Research）ユーティリティの使用例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
z = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点 / 運用上のポイント
- すべての「今日」を参照する処理は、ルックアヘッドバイアスを避ける設計（関数呼び出し側で target_date を明示することを推奨）になっています。
- OpenAI 呼び出しにはリトライ・バックオフ・JSON 検証等の安全策を入れていますが、API キーや費用管理は運用側で行ってください。
- J-Quants API へのアクセスはレート制限（120 req/min）を守る実装になっています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP（スコアリング）
  - regime_detector.py               — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETL 主要型の再エクスポート（ETLResult）
  - news_collector.py                — RSS ベースのニュース収集
  - calendar_management.py           — マーケットカレンダー / 営業日ロジック
  - quality.py                       — データ品質チェック
  - stats.py                         — 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py                         — 監査ログ用スキーマ初期化
- research/
  - __init__.py
  - factor_research.py               — ファクター計算（momentum/volatility/value）
  - feature_exploration.py           — forward returns / IC / summary / rank
- research/*（その他リサーチ用ユーティリティ）

ドキュメント / 設計上の注記
-------------------------
- 各モジュール冒頭に設計方針と処理フローのコメントがあり、バックテストや運用のための注意点が書かれています（例: look-ahead bias の防止、冪等性、API リトライ挙動、データ品質ポリシーなど）。
- news_collector は SSRF / XML 攻撃対策やレスポンスサイズ上限など多数の防御策を組み込んでいます。
- jquants_client は ID トークン自動リフレッシュ、固定間隔の RateLimiter、ページネーション対応を備えています。

開発・テスト
-------------
- ユニットテストでは外部 API 呼び出し（OpenAI/J-Quants/URL fetch）をモックすることを想定しています（モジュール内で _call_openai_api や _urlopen を差し替え可能）。
- 自動環境変数ロードを無効にするテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------
（ライセンス情報・貢献方法はリポジトリに応じて記載してください）

最後に
-------
この README はコードベースの主要機能と使い方をまとめた簡易ドキュメントです。各モジュール内の docstring やコメントに実装上の注意が多数ありますので、利用・拡張の際は該当ソースの先頭コメントを参照してください。質問や補足が必要であればお知らせください。