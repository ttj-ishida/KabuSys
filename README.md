# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM によるニュースセンチメント評価、ファクター計算、監査ログスキーマや市場カレンダー管理などを一貫して提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない）
- DuckDB を中心としたローカルデータストア
- 冪等性（ON CONFLICT / idempotent 保存）と堅牢なリトライ処理
- 外部 API 呼び出しは明示的に注入可能（テスト容易性を確保）

---

## 機能一覧
- 環境変数 / .env の自動読み込み（プロジェクトルート基準）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レートリミット管理・トークン自動リフレッシュ・リトライ
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）・前処理・raw_news 保存（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュース NLP（銘柄別スコアリング）
- 市場レジーム判定（MA + マクロニュース LLM 合成）
- リサーチ用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化ユーティリティ
- 市場カレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）

---

## セットアップ手順

推奨 Python バージョン: 3.10+

1. リポジトリをチェックアウト
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限（例）
     - pip install duckdb openai defusedxml
   - 開発時はプロジェクトルートに requirements.txt があればそれを使用:
     - pip install -r requirements.txt
   - 開発編集モードでインストール:
     - pip install -e .

4. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動で `.env` と `.env.local` を読み込みます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の主要環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定を使う場合）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注系を使う場合）
   - その他の設定例（.env に記述）:
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

   .env の読み込み仕様について：
   - OS 環境変数 > .env.local > .env の優先順位でマージします。
   - .env のパースはシェル風（export KEY=val / クォート / コメント）に対応します。

---

## 使い方（主な API 例）

以下は最小限の使用例です。実際にはログ設定やエラーハンドリングを追加してください。

準備: DuckDB 接続を作成する例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20), id_token=None)
print(result.to_dict())
```

2) ニュースのセンチメントスコア（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {written} symbols")
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB 初期化（監査専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成される
```

5) リサーチ用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

6) 市場カレンダー関数の利用例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
is_trade = is_trading_day(conn, d)
next_trade = next_trading_day(conn, d)
```

---

## 注意事項 / 実装上のポイント
- OpenAI 呼び出しには gpt-4o-mini を想定した JSON Mode を使用しています。API の仕様やレスポンスフォーマットの変更に注意してください。
- J-Quants へのリクエストはレート制限・リトライ・ID トークン自動リフレッシュを内蔵しています。大量の同時リクエストは避ける設計です。
- ETL / DB 書き込みは主に DuckDB で行います。DuckDB の executemany の仕様（空リストバインド不可など）に注意した実装になっています。
- ニュース収集では SSRF 対策（スキーム制限・プライベートホストチェック・リダイレクト検査）と XML パース安全化（defusedxml）を行っています。
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。配布後やインストール先の挙動に注意してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（銘柄別）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - calendar_management.py         — マーケットカレンダー管理
    - news_collector.py              — RSS 収集・前処理
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore 等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py         — 将来リターン/IC/統計サマリー

その他の補助モジュールやユーティリティが同階層に存在します。

---

## コントリビュート / テスト
- 新しい機能を追加する際はルックアヘッドバイアスを導入しないよう注意してください（バックテストとの整合性が重要です）。
- 外部 API 呼び出し部は差し替え可能に設計されているため、ユニットテスト時はモックしてテストしてください（例: _call_openai_api や _urlopen のモック）。
- .env の自動読み込みを無効化したいテストは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README に追加したい「具体的なコマンド例」「.env.example の雛形」などがあれば教えてください。README をそれに合わせて拡張します。