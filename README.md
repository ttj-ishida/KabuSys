# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP、マーケットカレンダー管理、リサーチ用のファクター計算、監査ログ（オーダー追跡）など、アルゴリズムトレード基盤で必要となる主要機能をモジュール化して提供します。

主な設計思想：
- ルックアヘッドバイアスを避ける（date.today()／datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータベースによる ETL / 分析
- 外部API呼び出し（J-Quants / OpenAI 等）はリトライ・レート制御・フォールバックを備える
- 冪等性（ON CONFLICT / idempotent）を重視した保存処理

---

## 機能一覧

- 環境・設定管理
  - `.env` / `.env.local` からの自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準）
  - 必須環境変数のラップ（`kabusys.config.settings`）

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（株価、財務、上場情報、マーケットカレンダー）
  - ETL パイプライン（差分更新・バックフィル・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions のテーブル設計と初期化）

- AI・NLP（kabusys.ai）
  - ニュースセンチメントスコアリング（OpenAI：gpt-4o-mini 使用、JSON Mode）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化ユーティリティ

- ユーティリティ
  - 汎用統計（z-score 正規化）
  - DuckDB に対する冪等保存ユーティリティ群

---

## 必要な環境・依存関係

- Python 3.10+
- 主な依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## 環境変数（主なもの）

以下は本システムで参照される代表的な環境変数です。`.env` / `.env.local` をプロジェクトルートに置くことで自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（少なくとも動かす機能に応じて設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（`kabusys.data.jquants_client.get_id_token` で使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等に利用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトがあるもの:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: `http://localhost:18080/kabusapi`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視等）ファイルパス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV — 環境 (`development` / `paper_trading` / `live`)（デフォルト: `development`）
- LOG_LEVEL — ログレベル (`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`)（デフォルト: `INFO`）

OpenAI 関連:
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp, regime_detector などで使用）。関数呼び出し時に引数で渡すことも可能。

.env 例（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに requirements / pyproject があればそちらを利用してください。なければ最低限以下をインストールします：
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発時はパッケージを編集可能モードでインストールすることを推奨：
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成して上の必須変数を設定してください。
   - 自動読み込みを無効にしたい場合は `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`（UNIX 系）などを設定します。

---

## 使い方（簡単なコード例）

以下は主要な機能を Python から呼び出す例です。DuckDB はライブラリで直接接続します。

- DuckDB 接続確立（デフォルトパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア生成（OpenAI API キーは環境変数か引数で渡す）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env OPENAI_API_KEY を参照
print(f"written scores: {written}")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB 初期化（別ファイルで監査ログを分離したい場合）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db = init_audit_db(Path("data/audit.duckdb"))
# これで signal_events / order_requests / executions 等が作成されます
```

- ファクター計算・リサーチ例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

---

## 自動 .env 読み込みの仕様

- パッケージ初期化時に `.env` と `.env.local` をプロジェクトルートから読み込みます（ルート検出: 親ディレクトリに `.git` または `pyproject.toml` がある場所）。
- 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`
- テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL の公開インターフェース（ETLResult）
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py — RSS ニュース取得と前処理
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ
    - audit.py — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

（上記は主要ファイルのみ抜粋。実際のリポジトリに他の補助モジュールがある場合があります）

---

## 運用上の注意・トラブルシューティング

- OpenAI / J-Quants の API キーは外部サービスの利用制限（料金・レート）に依存します。実稼働環境でのレート・コスト管理を必ず行ってください。
- news_nlp / regime_detector は外部 API 呼び出しにフォールバックとリトライを実装していますが、API が利用できない場合はスコアが 0 にフォールバックするなどの挙動になります（フェイルセーフ）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、空チェックが実装されています。独自にコードを拡張する際は注意してください。
- ETL は部分失敗に対しても他のステップを継続する設計です。ETLResult にエラー・品質問題が記録されるので監視してください。
- RSS フェッチは SSRF 対策（ホストの私的IP検査、リダイレクト検査）や受信サイズ制限を実装しています。外部 RSS の仕様変更により取得失敗が発生する可能性があります。

---

## 貢献・拡張

- 新しい AI モデルやニュースソースの追加、ETL の対応 API 増加、監査テーブルの拡張など、モジュール単位で拡張できるよう設計されています。
- 単体テストを追加する際は、API 呼び出し部分（OpenAI / J-Quants / ネットワーク）をモックすることを推奨します。既存コードはテスト用に内部の HTTP/API 呼び出しを差し替えやすいように実装されています。

---

必要に応じて README に追加したい内容（例：実際の requirements.txt、CI/CD の手順、運用監視設定、サンプル .env.example ファイルの追加など）があれば教えてください。