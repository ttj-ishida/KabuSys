# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（ミニマル実装）。  
データ取得（J-Quants）、ETL、ニュースセンチメント（OpenAI）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（発注/約定トレース）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date/target_date を明示的に渡す）
- DuckDB を中心としたオンディスク DB を利用
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを組み込む
- 冪等性（ETL の ON CONFLICT / トランザクション制御）を重視

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - settings オブジェクト経由で各種設定取得（J-Quants トークン、OpenAI、Kabu API、DB パス 等）
- データ ETL（J-Quants API）
  - 日次株価（OHLCV）取得と DuckDB への保存（ページネーション・リトライ・レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダーの取得・保存
  - run_daily_etl による一括 ETL（品質チェックオプション付き）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合を検出するチェック群
- ニュース収集 / NLP（OpenAI）
  - RSS 取得（SSRF対策・サイズ制限・前処理）
  - ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores に格納
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成してレジーム（bull/neutral/bear）判定
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理するユーティリティ
  - init_audit_db / init_audit_schema

---

## 要件

- Python 3.10+
- 必要なライブラリ（主なもの）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装しているため最小限。プロジェクトの運用用途に応じて追加依存が発生する可能性あり）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt があればそれを使用
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリを取得
   - 開発中: git clone ...

2. 仮想環境の作成と依存ライブラリのインストール
   - 上記「要件」を参照

3. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読込停止）。
   - 必要な環境変数（例）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI
     OPENAI_API_KEY=your_openai_api_key

     # kabuステーション API
     KABU_API_PASSWORD=your_kabu_password
     # KABU_API_BASE_URL は省略時 http://localhost:18080/kabusapi

     # Slack 通知
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_channel_id

     # DB パス（任意）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 動作環境
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須のキーは settings オブジェクトのプロパティでも参照され、未設定時は ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

4. DuckDB データベース初期化（監査用など）
   - 監査ログ用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 通常の ETL 等で使う DB は settings.duckdb_path を参照して接続してください:
     ```python
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（主要な API と実行例）

基本は DuckDB 接続（duckdb.connect）を作り、該当モジュールの関数を呼び出します。全ての関数は target_date を明示的に渡す設計です。

- ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（ai_scores 書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算（例: momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

- 監査スキーマ初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
# conn は既存の duckdb 接続
init_audit_schema(conn, transactional=True)
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI API キーは関数側で引数 api_key に渡せます（省略時は環境変数 OPENAI_API_KEY を使用）。
- 自動ロードされる .env / .env.local はプロジェクトルート（.git または pyproject.toml を基準）から探索されます。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要モジュールと概要です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定の管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI 呼び出し・ai_scores への書き込み
    - regime_detector.py
      - ETF 1321 の MA200 とニュースセンチメントの合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数）
    - pipeline.py
      - run_daily_etl 等の ETL パイプライン
    - etl.py
      - ETL の公開インターフェース（ETLResult の再エクスポート等）
    - calendar_management.py
      - 市場カレンダー管理・営業日判定ユーティリティ
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL・初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value などのファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー 等
  - （将来/別モジュール）strategy, execution, monitoring パッケージを参照するエクスポートあり

---

## 運用上の注意事項

- Look-ahead バイアス防止のため、ライブラリ内部は date/times の扱いを厳格にしています。バックテスト等で使用する際は target_date を正しく渡してください。
- 外部 API（J-Quants、OpenAI）を利用するため、それぞれの利用規約とレート制限に注意してください。ライブラリは基本的なレート制御/リトライを実装していますが、運用量に応じた追加対策が必要です。
- DuckDB のバージョンやシリアライズ仕様により挙動差が出る場合があります。実運用ではバージョン固定を推奨します。
- news_collector は RSS の外部取得を行います。SSRF・サイズ上限・XML 攻撃対策（defusedxml 等）を実装していますが、運用環境のネットワークポリシーに注意してください。

---

## 貢献 / 拡張案

- strategy / execution モジュールの実装（戦略のシグナル生成 -> 発注フロー）
- 監視/モニタリング（Slack 通知・Prometheus メトリクス等）
- バッチスケジューラ（Airflow / cron との統合サンプル）
- テストカバレッジの拡充（外部 API をモックしたユニットテスト）

---

不明点や README に追記してほしい情報があれば教えてください。テスト用の実行スクリプトや .env.example のテンプレート生成なども作成できます。