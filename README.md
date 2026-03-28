# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README（日本語）

このリポジトリは日本株のデータ取得・品質管理・特徴量（ファクター）計算、ニュースの NLP スコアリング、さらに市場レジーム判定や監査ログの仕組みを提供するモジュール群を含みます。DuckDB を用いたローカル DB を想定し、J-Quants / JPYX 等の外部 API と連携する ETL・Client 実装を備えます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支える「データ基盤」「研究（リサーチ）」「AI ニュース解析」「監査／実行管理」などのコンポーネントを提供する Python ライブラリです。設計方針として以下を重視しています。

- ルックアヘッドバイアスの防止（内部で date.today() を不必要に参照しない等）
- DuckDB を用いた高パフォーマンスなローカルデータ管理
- J-Quants など外部 API との安全なやり取り（レート制限、リトライ、トークンリフレッシュ）
- OpenAI を利用したニュースセンチメント分析（JSON mode を使用）
- ETL / 品質チェック / 監査ログの冪等（idempotent）設計

バージョン: 0.1.0

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出：`.git` または `pyproject.toml`）
  - 必須環境変数取得時のバリデーション（Settings クラス）

- データ取得・ETL（kabusys.data）
  - J-Quants クライアント（fetch/save: 日足、財務、上場情報、カレンダー）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去）
  - 監査ログ（signal_events / order_requests / executions テーブル定義・初期化）
  - 統計ユーティリティ（Zスコア正規化など）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ、ランキング等）

- AI（kabusys.ai）
  - ニュースの NLP スコアリング（gpt-4o-mini を使用、JSON Mode）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成）

- その他
  - DuckDB での冪等保存（ON CONFLICT / INSERT … DO UPDATE）
  - リトライ・指数バックオフ・レート制限実装

---

## 前提 / 必要要件

- Python 3.10 以上（型ヒントに `X | Y` 構文を使用）
- 必要主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（開発環境では追加で linters / test ライブラリを用いる可能性あり）

例: 必要パッケージをインストールする最小例
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクトに requirements.txt があればそれを利用してください。

---

## 環境変数（主なもの）

Settings クラスで参照される主要な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — デフォルト DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）

自動 .env 読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で読み込みます（`.env.local` が上書き）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

例: .env の最小例
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements.txt があれば:
   # pip install -r requirements.txt
   ```

2. 環境変数を設定
   - ルートに `.env` を作成するか、CI あるいはシステム環境変数として設定します。
   - 必須変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI を使う場合）

3. DuckDB データベース準備（必要な場合）
   - 初期スキーマ作成等はアプリ側スクリプトで行いますが、監査 DB を別途初期化するユーティリティがあります（下記参照）。

---

## 簡単な使い方（コード例）

以下は代表的なユースケースの Python スニペット例です。実行前に環境変数を適切に設定してください。

- ETL（日次パイプライン）を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成する（OpenAI API キーが必要）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら OPENAI_API_KEY を参照
print(f"scored {n_written} codes")
```

- 市場レジーム判定を行う:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用の DuckDB を初期化する:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

注:
- AI 関連関数（news_nlp.score_news, regime_detector.score_regime）は api_key 引数を受け取ります。None を指定すると環境変数 OPENAI_API_KEY を参照します。
- ETL / save 関数は冪等に設計されています（ON CONFLICT … DO UPDATE）。

---

## 重要な設計上の注意点

- ルックアヘッドバイアス対策：各モジュール（news_nlp, regime_detector, research など）は内部で現在時刻を無差別に参照せず、target_date を明示して処理するように設計されています。バックテスト等で使う場合は target_date を適切に設定してください。
- 冪等性：API -> DB の保存は idempotent に設計（ON CONFLICT）されており、ETL の再実行に強いです。
- エラー処理：外部 API 呼び出しはリトライ・バックオフ・フォールバック値を持ち、致命的な失敗時でもシステム全体が一気に停止しないようになっています（ただし重要な環境変数の未設定は例外を送出）。
- セキュリティ：news_collector 等で SSRF 対策、defusedxml による XML パース保護、RSS の最大サイズ制限等を実装しています。

---

## ディレクトリ構成

主要なファイルとモジュールを抜粋して示します（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュース NLP（OpenAI）スコアリング
    - regime_detector.py   -- 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（fetch/save, rate limit, retry）
    - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
    - etl.py               -- ETLResult の再エクスポート
    - calendar_management.py -- 市場カレンダー管理（営業日判定、update job）
    - stats.py             -- 統計ユーティリティ（zscore_normalize）
    - quality.py           -- データ品質チェック
    - audit.py             -- 監査ログテーブル定義・初期化
    - news_collector.py    -- RSS ニュース収集（SSRF 対策・前処理）
  - research/
    - __init__.py
    - factor_research.py   -- ファクター計算（momentum/value/volatility など）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリ等
  - monitoring/ (存在が暗示されているが実装は省略されている領域)
  - execution/, strategy/ (戦略・発注のためのモジュール群（エントリは __all__ に含まれる）)

（上記はコードベースの抜粋構成です。実運用では追加の CLI スクリプト、デプロイ設定、テストコードなどが存在する場合があります）

---

## よくある操作・トラブルシューティング

- .env が読み込まれない
  - 自動ロードはプロジェクトルートを .git または pyproject.toml で検出します。プロジェクトルートが検出できない場合、自動ロードはスキップされます。必要なら明示的に環境変数をシェルで export してください。
  - 自動ロードを無効にしている場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をチェック。

- OpenAI へのリクエストが失敗する
  - OPENAI_API_KEY が未設定だと関数は ValueError を送出します。
  - rate limit・ネットワーク断・一時的な 5xx は内部でリトライします。重大な問題はログを確認してください。

- J-Quants の認証が必要な場合
  - JQUANTS_REFRESH_TOKEN を設定し、jquants_client.get_id_token がトークンを取得します。401 が返れば自動でリフレッシュし1回リトライする設計です。

---

## 開発・貢献

コードの追加や修正を行う際は次を推奨します。

- type hints を守る（Python 3.10+ の構文を使用）
- ルックアヘッドバイアスに注意して target_date を適切に渡す
- 外部 API 呼び出しはモック化してユニットテストを書く（news_nlp/regime_detector は API 呼び出し抽象化用関数をモック可能）
- DB 操作はトランザクションや ROLLBACK の挙動を意識する

---

以上が KabuSys の README（日本語）です。README に追加したい具体的なセクション（例: CLI コマンド一覧、実運用時のデプロイ手順、詳細な .env.example など）があれば指示ください。