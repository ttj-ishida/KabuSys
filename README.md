# KabuSys

日本株向けのデータプラットフォーム兼自動売買（研究・運用）ライブラリ。  
DuckDB をデータ層に使い、J-Quants / RSS / OpenAI 等と連携してデータ収集、品質チェック、ファクター計算、ニュースNLP、マーケットレジーム判定、監査ログなどを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない等）
- DuckDB を用いた冪等な ETL / 保存ロジック
- OpenAI 呼び出しはリトライ・フェイルセーフ設計
- DB による監査トレーサビリティ（UUID ベース）

---

## 機能一覧

- 環境設定管理（.env の自動読み込み / 必須設定チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - Rate limiting / リトライ / トークン自動リフレッシュ対応
- ETL パイプライン（日次 ETL：calendar / prices / financials / 品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）および前処理（URL 正規化、SSRF 対策）
- ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア生成
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 統計ユーティリティ（Zスコア正規化、将来リターン、IC 等）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 必要環境

- Python 3.10+（Union types `X | None` を利用しているため）
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他（標準ライブラリ中心に実装されているため最小限で済みます）

例: requirements.txt を作る場合の最低候補
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン／配置（src レイアウトを想定）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発インストール）pip install -e .
4. 環境変数 / .env を準備
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（jquants_client 用）
     - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector 用）※関数呼び出し時に引数で渡すことも可能
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（kabu 呼び出し用）
     - SLACK_BOT_TOKEN : Slack 通知用トークン
     - SLACK_CHANNEL_ID : 通知先チャネル ID
   - 任意 / デフォルトあり
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）

例 .env（簡易）
"""
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
"""

---

## 使い方（代表的なコード例）

以下は主要ユーティリティの使い方例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) が返す connection）を受け取ります。

- DuckDB 接続作成（ファイル DB）
"""
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
"""

- 日次 ETL を実行する（run_daily_etl）
"""
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
"""

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY でも渡せます）
"""
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", written)
"""

- 市場レジーム判定
"""
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
"""

- ファクター計算（研究用）
"""
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
"""

- 監査ログ DB の初期化（監査用専用 DB）
"""
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルへ書き込みが可能
"""

注意点：
- OpenAI 呼び出しはモデル gpt-4o-mini 等を使用しており、API レートやコストに注意してください。API 呼び出し失敗時はフェイルセーフでスコアを 0 や空にする設計です。
- J-Quants API はレート制限（120 req/min）に合わせた内部 RateLimiter を持ちます。
- ETL / 保存処理は冪等（ON CONFLICT を使用）を基本にしています。

---

## 主要モジュール / ディレクトリ構成

以下はコードベースの主要ファイルと簡単な説明です（src/kabusys 配下）:

- kabusys/
  - __init__.py
    - パッケージメタ情報（__version__ 等）
  - config.py
    - 環境変数・.env 管理、Settings オブジェクト（JQUANTS_REFRESH_TOKEN / SLACK 等）
  - ai/
    - __init__.py
      - score_news のエクスポート
    - news_nlp.py
      - ニュースの集約・OpenAI による銘柄別センチメント付与（ai_scores への書き込み）
    - regime_detector.py
      - ETF(1321)のMA200乖離とマクロニュースのLLMスコアを合成して market_regime に書き込み
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数、認証・リトライ・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダー管理 / 営業日判定（is_trading_day / next_trading_day 等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - news_collector.py
      - RSS 収集・前処理・SSRF 対策・raw_news 保存補助
    - audit.py
      - 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
      - 研究向けユーティリティのエクスポート
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py
      - 将来リターン計算、IC、ファクター統計サマリ、ランク関数等

（上記の各モジュール内で DuckDB 接続を引数として受け取る形で動作します。）

---

## 開発・運用上の注意

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants のキー管理:
  - OpenAI キーは関数引数で渡すことも可能（テスト時に差し替えやすくするため）。環境変数 OPENAI_API_KEY を使う場合もあります。
  - J-Quants は refresh token を設定し、get_id_token が内部で id_token を取得してキャッシュします。
- エラーハンドリング:
  - ネットワーク系や外部 API エラーは内部でリトライやフォールバックを行い、致命的でない限り処理を継続する設計です。ログ（LOG_LEVEL）で挙動を確認してください。
- DuckDB バージョンや executemany の挙動に依存する箇所があるため、DuckDB のバージョン差分に注意してください（コード内にも互換性対策あり）。

---

## サンプルワークフロー

1. DuckDB を初期化（スキーマは別途提供・初期化する想定）。監査DBは init_audit_db で別管理可能。
2. 日次 ETL 実行（run_daily_etl）で calendar/prices/financials を取得・保存。
3. news_collector で RSS を定期取得・保存（raw_news / news_symbols の作成）。
4. score_news でニュースをスコアリングし ai_scores に保存。
5. score_regime でマーケットレジームを判定・保存。
6. research モジュールでファクター計算・評価を行い、戦略に繋げる。
7. 戦略が生成したシグナルは監査テーブルに保存し、order_requests を通して発注・約定を追跡する。

---

必要であれば、README に入れる具体的な .env.example、requirements.txt、あるいはサンプルスクリプト（ETL バッチ / ニュース収集 cron 例 / Slack 通知の例）も作成します。どの追加例が欲しいか教えてください。