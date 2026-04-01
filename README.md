# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
ETL（J-Quants）による市場データ取得、ニュース収集・LLMを用いたニュースセンチメント、ファクター計算、監査ログ（発注トレース）などのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の要素を含むモジュール群から構成されています。

- data: J-Quants API からのデータ取得（株価・財務・カレンダー）、ETL パイプライン、ニュース収集、品質チェック、監査ログ（audit）等
- ai: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定（ETF + マクロセンチメント）
- research: ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量評価ユーティリティ
- config: 環境変数・設定管理
- その他: 実行・戦略・監視モジュール群（package export の想定）

設計方針の要点は次の通りです。

- ルックアヘッドバイアスを避ける（内部で date.today() を勝手に参照しない等）
- DuckDB を主要なオンディスク DB として利用（ETL や監査ログ）
- OpenAI（gpt-4o-mini 等）や J-Quants API を利用する際はリトライ・フェイルセーフを備える
- 冪等性（ETL／保存処理）を重視

---

## 主な機能一覧

- ETL（data.pipeline）
  - 日次 ETL（市場カレンダー / 株価日足 / 財務データ）run_daily_etl
  - 差分取得・バックフィル・品質チェックの統合
- J-Quants クライアント（data.jquants_client）
  - 認証（refresh token → id token）
  - daily_quotes / financial statements / market calendar の取得と DuckDB への保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ニュース収集（data.news_collector）
  - RSS 取得（SSRF 対策、gzip 対応、サイズ制限）
  - 記事正規化・ID 生成・raw_news への冪等保存を想定
- ニュース NLP（ai.news_nlp）
  - ニュースを銘柄ごとに集約し OpenAI に送りセンチメント（ai_scores）を生成
  - チャンク処理、バッチ送信、レスポンス検証、スコアクリップ
- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の200日 MA 乖離＋マクロニュース LLM スコアの加重合成 → market_regime 登録
- 研究用ユーティリティ（research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- 監査ログ（data.audit）
  - signal_events / order_requests / executions など発注フローのトレーサビリティ / 初期化ユーティリティ

---

## 前提・依存関係

- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、OpenAI、RSS ソース 等）
- J-Quants のリフレッシュトークン、OpenAI API キー などの環境変数

必要なパッケージはプロジェクトに requirements.txt があればそれを使うか、下記を pip install してください（例）:

pip install duckdb openai defusedxml

（実際の requirements はプロジェクト配布物に合わせてください）

---

## セットアップ手順

1. リポジトリをクローン／取得

   git clone <repo-url>
   cd <repo>

2. 開発インストール（任意）

   python -m pip install -e .

3. 環境変数の準備

   プロジェクトルートに .env / .env.local を配置できます。config モジュールは自動で .env をロードします（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。

   自動ロードを無効化したい場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（必須／デフォルト）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - OPENAI_API_KEY (必須 for AI modules unless api_key を関数に渡す)
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知用（未使用箇所がある場合は任意）
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - PID_FILE_PATH (任意) — デフォルト: data/execution.pid
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT (任意)
   - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. ディレクトリの初期作成（DB 保存先など）

   mkdir -p data

---

## 使い方（コード例）

以下は代表的な使用例です。各関数は DuckDB 接続（duckdb.connect(...) の戻り値）を受け取る設計です。

- DuckDB 接続の作成例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査 DB の初期化（audit 用の独立 DB を作る）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 日次 ETL の実行:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI KEY を渡すか環境変数 OPENAI_API_KEY をセット）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"Scored {count} symbols")
```

- 市場レジーム判定:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算（例: モメンタム）:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の mom_1m / mom_3m / mom_6m / ma200_dev を含む dict のリスト
```

注意点:
- OpenAI 呼び出しは API レートや料金に注意してください。テスト時は関数内部の _call_openai_api をモックできます。
- J-Quants からデータを取得するためには有効な JQUANTS_REFRESH_TOKEN が必要です。

---

## よく使うユーティリティ

- settings: 環境変数を扱う簡単なインターフェース

```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live, settings.log_level)
```

- data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- data.quality.run_all_checks(conn, target_date=..., reference_date=...)

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールとファイル一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py       — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント & 保存
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETL の公開型再エクスポート
    - news_collector.py        — RSS 取得・前処理
    - calendar_management.py   — 市場カレンダー判定・更新ジョブ
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                 — 監査ログテーブル初期化・ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — forward returns / IC / summary / rank
  - ai, research パッケージ等の __all__ 指定により API を整理

---

## 運用上の注意

- センチメントや LLM 呼び出しは失敗した場合フェイルセーフ（スコア 0.0）にフォールバックする設計ですが、運用時のログ監視は必須です。
- ETL は J-Quants のレート制限を順守するよう内部で制御していますが、頻度や大量データ取得時は注意してください。
- DuckDB の executemany に空リストを渡せないバージョンを考慮した実装になっていますが、DuckDB バージョン依存の挙動には留意してください。
- 監査ログは削除しない前提です。データサイズ管理（圧縮・アーカイブ）を検討してください。

---

## 貢献・拡張

- 新しいニュースソースの追加は data.news_collector.DEFAULT_RSS_SOURCES を拡張し、raw_news/news_symbols の流れに接続してください。
- 新しいファクターや戦略ロジックは research パッケージに追加し、監査ログ（signal_events → order_requests → executions）のトレースを行ってください。
- テストは OpenAI/J-Quants 呼び出しをモックして行うことを推奨します（各モジュールはモック差替えポイントを想定して作られています）。

---

README に不足している具体的な運用手順（CI/CD、デプロイ、cron ジョブ例など）があれば、その用途に合わせたサンプルを追記できます。必要であれば教えてください。