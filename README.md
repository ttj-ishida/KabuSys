# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLPによるセンチメント評価、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

主な設計方針
- DuckDB を中心に軽量で高速なローカルデータ管理
- Look‑ahead バイアス対策（内部で date.today() を不用意に参照しない設計）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備えた実装
- 冪等性（API→DB 保存は ON CONFLICT 等で上書き）を重視

---

## 機能一覧

- データ（data）
  - J-Quants API クライアント（fetch / save）: 株価日足、財務、上場銘柄、マーケットカレンダー
  - ETL パイプライン（run_daily_etl 等）: 差分取得・保存・品質チェック
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログスキーマ初期化（audit.init_audit_db / init_audit_schema）

- 研究（research）
  - ファクター計算: モメンタム、ボラティリティ、バリュー等
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - zscore 正規化ユーティリティ

- AI（ai）
  - ニュースセンチメント評価（news_nlp.score_news）
  - マーケットレジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、結果を DuckDB に保存する設計

- 共通 / 設定
  - 環境変数管理（.env 自動読み込み、Settings クラス）
  - 監視設定（PID ファイルパス、CPU/MEM/DISK 閾値 など）

---

## セットアップ手順

前提
- Python 3.10+（コードは型アノテーションに union 型等を使用）
- DuckDB を利用するための環境

1. リポジトリをクローン（あるいはソースを入手）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   基本的に次をインストールしてください（プロジェクトに requirements.txt があればそちらを利用）。
   ```
   pip install duckdb openai defusedxml
   ```
   （ネットワーク等を扱う標準ライブラリのみで実装されていますが、OpenAI・DuckDB・defusedxml は必須です）

4. 開発インストール（オプション）
   ```
   pip install -e .
   ```

5. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を作成すると自動で読み込まれます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例（.env.example 相当）
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 必須項目は Settings クラスのプロパティで _require() によりチェックされます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD は呼び出し箇所で必要）。

---

## 使い方（主要な例）

基本的に DuckDB 接続を生成して各モジュールへ渡します。

- DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアを生成（OpenAI API キーは OPENAI_API_KEY 環境変数か引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- マーケットレジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡すことも可
```

- 監査ログ DB 初期化（監査専用DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はスキーマを作成し接続を返す
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict のリスト
```

注意点
- OpenAI 呼び出しには API キー（OPENAI_API_KEY）が必要です。news_nlp / regime_detector はキーがない場合 ValueError を送出します。
- ETL や AI モジュールは外部 API 呼び出しを伴うため、ネットワーク・認証情報の準備が必要です。
- 自動ロードされる .env は OS 環境変数より低優先度で `.env.local` が上書きできます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（実運用で注文周りを使う場合）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（監視等で利用）
- SLACK_CHANNEL_ID       : Slack チャネル ID
- DUCKDB_PATH            : デフォルト DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（default: data/monitoring.db）
- PID_FILE_PATH          : 実行プロセスの PID ファイルパス（default: data/execution.pid）
- KABUSYS_ENV            : environment（development | paper_trading | live）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

（上記は config.Settings にて getter が定義されています）

---

## 主要モジュール・ディレクトリ構成

以下はソースツリーの概要（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュースセンチメント評価（OpenAI 経由）
    - regime_detector.py         -- ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（fetch/save）
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - etl.py                     -- ETLResult 型の再エクスポート
    - calendar_management.py     -- マーケットカレンダー管理（営業日判定等）
    - news_collector.py          -- RSS ニュース収集（SSRF対策、正規化）
    - quality.py                 -- データ品質チェック
    - stats.py                   -- 統計ユーティリティ（zscore 正規化）
    - audit.py                   -- 監査ログスキーマ初期化 / DB 作成
  - research/
    - __init__.py
    - factor_research.py         -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py     -- 将来リターン・IC・統計サマリ等
  - ai/、research/ は研究・分析・AI 用の主要機能群です。

---

## 実運用上の注意・設計上のポイント

- Look‑ahead バイアス対策
  - 日付参照は target_date ベースで行い、内部で現在時刻を直接参照する実装を避けています（バックテストとの整合性向上）。
- 再現性・冪等性
  - DB への保存は ON CONFLICT 等を用いて冪等に実行されます。
- フェイルセーフ
  - 外部 API でのエラーは多くの場合フェイルセーフ（スコアを 0 にする、処理をスキップする等）で継続する設計です。
- セキュリティ
  - RSS フェッチでは SSRF 対策、XML パースに defusedxml を利用しています。
- テスト
  - AI 呼び出し部分などは内部で _call_openai_api を抽象化しており、ユニットテストで置き換え可能です。

---

## よくある利用フロー（例）

1. .env を用意し必要な API キーを設定
2. DuckDB（settings.duckdb_path）へ接続
3. 初回: data.audit.init_audit_db() などで監査 DB を初期化
4. 日次バッチ: data.pipeline.run_daily_etl() を Cron / Airflow 等で定期実行
5. 毎朝: ai.news_nlp.score_news() → ai_scores にスコア書込み
6. ai.regime_detector.score_regime() で市場レジームを判定し、戦略側へ反映

---

## 開発・貢献

- コードスタイル、テスト、CI の整備をお願いします。外部 API を使う箇所はモック化して単体テストを作成してください。
- セキュリティ関連（RSS / HTTP）の変更は慎重にレビューしてください。

---

必要であれば README に追記します（例: CI 実行方法、詳細な DB スキーマ、運用手順、Docker コンテナ化、より詳細な .env.example）。