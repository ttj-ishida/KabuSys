# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLPスコアリング、ファクター計算、監査ログ（オーディット）、市場レジーム判定など、バックテスト・運用に必要な基盤機能を提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの株価（日足）・財務データ・市場カレンダー取得（ページネーション・トークンリフレッシュ対応）
  - DuckDB へ冪等（ON CONFLICT）で保存
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS からの記事収集（SSRF 保護、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols テーブルへの冪等保存
- ニュース NLP / AI スコアリング
  - OpenAI（gpt-4o-mini + JSON mode）を用いた銘柄単位のセンチメント評価（score_news）
  - マクロニュースと ETF (1321) の MA200 乖離を統合した市場レジーム判定（score_regime）
  - 再試行・フォールバック・レスポンス検証を考慮した堅牢な実装
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC / 統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 発注フローのトレーサビリティをUUID連鎖で確保
- 設定管理
  - .env（.env.local）や環境変数からの設定自動読み込み（パッケージ内独自実装）

---

## 動作環境・依存

推奨 Python バージョン: 3.10+（本コードは `from __future__ import annotations` と型ヒントの近代機能を使用）  
主な依存パッケージ（最低限）:

- duckdb
- openai
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクト配布で requirements.txt / pyproject.toml があればそちらを利用してください。

---

## 環境変数（必須・任意）

config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（本プロジェクト内で Slack を利用する機能がある場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

AI 関連:
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime 等）

kabu ステーション（発注等）:
- KABU_API_PASSWORD — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）

データベース・監視等（任意: デフォルトあり）:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行 PID ファイル（デフォルト: data/execution.pid）

システム:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します。

.env の自動ロード順:
OS 環境変数 > .env.local（上書き） > .env（未上書き）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定 (.env/.env.local をプロジェクトルートに配置)
   - 必要な値（上記参照）を設定してください。

4. 初期 DB（監査DB）を作成（例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn を使ってクエリや初期化確認ができます
   ```

---

## 使い方（主要 API・実行例）

以下はライブラリを Python から直接呼ぶ最小の例です。DuckDB 接続は duckdb.connect(...) で取得します。

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（前日15:00〜当日08:30 JST のウィンドウを対象）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("data/kabusys.duckdb"))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの統合）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str("data/kabusys.duckdb"))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査テーブル初期化
```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI を使う関数は OPENAI_API_KEY を要求します（api_key 引数で上書き可能）。
- DuckDB 接続は呼び出し元で管理してください（同一接続で複数操作をまとめると効率的）。
- ETL / API 呼び出しはネットワーク通信を伴うため、適切なトークン / レート制御を行ってください。

---

## 開発者向けのヒント

- .env の自動ロードはパッケージ内で実施されています。テストなどで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しなどは内部で再試行ロジックを持ちますが、テスト時は該当モジュールの _call_openai_api をモックすると良いです（README のコード内でもその旨をコメントしています）。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、ライブラリ内では空チェックを行っています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に実装があります。主要ファイルを抜粋します:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント / 保存関数
    - pipeline.py            — ETL パイプライン / run_daily_etl
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — z-score 正規化等ユーティリティ
    - audit.py               — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（ファイルはさらに細かいユーティリティや内部関数を含みます。README では主要機能に焦点を当てています）

---

## ライセンス・貢献

このリポジトリに関するライセンス情報・貢献方法はリポジトリのトップレベルにある LICENSE / CONTRIBUTING.md を参照してください（存在しない場合は管理者に問い合わせてください）。

---

何か特定の使い方（例：kabu ステーションへの接続方法、Slack 通知のサンプル、CI での ETL 実行スクリプト作成など）について詳しいドキュメントが必要であれば教えてください。必要に応じて README を拡張してサンプル .env.example やコマンドラインスクリプト例も追加します。