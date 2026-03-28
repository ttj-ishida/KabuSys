# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリセット。  
ETL（J-Quants）→ データ品質チェック → 特徴量計算 → AI ニュースセンチメント → 市場レジーム判定 → 監査ログ（約定トレーサビリティ）といったワークフローを提供します。

バージョン: 0.1.0

---

## 特徴（概観）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レートリミット・自動リフレッシュ（401）・再試行（指数バックオフ）対応
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務）と品質チェックを一括実行
  - 差分取得・バックフィル（後出し修正吸収）対応
  - ETL 結果を ETLResult で集約
- データ品質チェック
  - 欠損、主キー重複、株価スパイク、将来日付／非営業日の検出
  - QualityIssue 型で詳細を返す（error / warning）
- ニュース収集
  - RSS フィード取得、URL 正規化、前処理、raw_news への冪等保存
  - SSRF 対策、受信サイズ上限、XML セキュリティ対策等を実装
- AI モジュール（OpenAI を利用）
  - ニュースごとの銘柄センチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）：ETF（1321）MA200 とマクロセンチメントの合成
  - JSON Mode（厳密な JSON 出力）とリトライ・フォールバックの設計
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン、IC（Spearman ランク相関）、Z スコア正規化など
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - UUID ベースのトレーサビリティ、冪等キー（order_request_id）による二重発注対策
- 市場カレンダー管理
  - JPX カレンダーを元に営業日判定・前後営業日探索・夜間バッチ更新ジョブを提供

---

## 必要条件 / 依存関係

- Python 3.10 以上（typing の | 型注釈を使用）
- 必須パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt があればそれを使用してください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注連携を使う場合）
- SLACK_BOT_TOKEN        : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID
- OPENAI_API_KEY         : OpenAI を使う処理（news_nlp / regime_detector）で必要

オプション:
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : environment（development / paper_trading / live）
- LOG_LEVEL              : ログレベル（DEBUG, INFO, ...）

config の利用例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

.env の行パーサーは export プレフィックス、クォート、インラインコメント等に対応しています。

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成と依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

3. 環境変数を用意（.env を作成）
   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABUS_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB の初期スキーマや監査 DB の初期化（必要に応じて）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用 DB（共通 DB）にスキーマを用意するスクリプトがあればそれを実行してください（プロジェクトに schema 初期化関数が存在する想定）。

---

## 使い方（主な API の例）

以下は Python スクリプトから直接呼び出す例です。

- DuckDB コネクションを作成して日次 ETL を実行:
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date 省略で今日（ローカルカレンダー考慮）
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数または api_key 引数で指定
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（regime_score を market_regime テーブルに書き込む）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログの初期化（トランザクションを使用）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへ書き込みが可能
```

- 研究用ユーティリティ（例: モメンタム計算）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

---

## 実装上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス回避のため、内部実装は date.today()/datetime.today() を直接参照しないか、引数で date を渡す設計を優先。
- API 呼び出しの失敗はフェイルセーフとして許容し、部分的にスキップして継続する設計が多い（特に AI モジュール、ETL の各段）。
- DuckDB への書き込みは可能な限り冪等に実装（ON CONFLICT 等）され、ETL はバックフィル機能で API の後出し修正を取り込む。
- ニュース収集は SSRF・XML 注入・Gzip bomb 等のセキュリティ対策を導入。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント解析（OpenAI 呼び出し・レスポンス検証・バッチ処理）
    - regime_detector.py     # マクロ + ETF MA200 を合成した市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py # マーケットカレンダー管理・営業日判定
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETL の公開結果クラス再エクスポート（ETLResult）
    - jquants_client.py      # J-Quants API クライアント（取得＋保存関数）
    - news_collector.py      # RSS ニュース収集・前処理
    - quality.py             # データ品質チェック（欠損・スパイク・重複・日付）
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               # 監査ログ（signal/order/execution）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # Momentum/Volatility/Value の計算
    - feature_exploration.py # forward returns, IC, factor_summary, rank
  - ai/
    - (上記)
  - research/
    - (上記)

各モジュールは DuckDB 接続や API キーの注入を想定しており、直接本番発注を行う箇所は分離された設計です。

---

## テスト / 開発上のヒント

- config.py は自動でプロジェクトルート（.git または pyproject.toml）配下の `.env` / `.env.local` を読み込みます。テスト中に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や外部 API 呼び出し箇所は内部の `_call_openai_api` 等を patch してユニットテスト可能です（モック差し替え想定）。
- DuckDB に対する executemany の空リストは一部バージョンの制約があるため、呼び出し前に空チェックを行っています。テスト時も同様に確認してください。

---

## 連絡先 / ライセンス

本 README はコードベースに基づく概要ドキュメントです。詳細な仕様（データベーススキーマ、ETL スケジュール、運用手順など）は別途ドキュメント（Design/Operational md）を参照してください。ライセンスや貢献ルールはリポジトリのルートにある LICENSE / CONTRIBUTING を確認してください。

---

README の補足や特定機能（例: 発注連携、Slack 通知、CI 設定）のドキュメント化を希望する場合は、目的と必要な情報を教えてください。