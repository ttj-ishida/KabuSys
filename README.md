# KabuSys

KabuSys は日本株向けのデータ基盤・分析・レジーム判定・監査ログを備えた自動売買支援ライブラリです。J-Quants / RSS / OpenAI（LLM）などの外部データを取り込み、ETL、品質チェック、ファクター計算、ニュース NLP、レジーム判定、監査テーブル初期化などを行えます。

## 主な特徴（機能一覧）
- データ取得 / ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、JPX マーケットカレンダー等を差分取得・保存
  - 差分更新・バックフィル対応・ページネーション・自動トークンリフレッシュ
- データ品質チェック
  - 欠損データ、スパイク検出、重複、日付不整合（将来日付・非営業日データ）を検出
- ニュース収集 / NLP
  - RSS フィードからニュースを収集（SSRF対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（ai_scores）の算出
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメントの合成）
- リサーチ／ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース、外部 API 呼び出しなし）
  - 将来リターン計算、IC（スピアマン順位相関）、Zスコア正規化 等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化ユーティリティ
  - 発注の冪等性・ステータス管理を想定したスキーマ
- 汎用ユーティリティ
  - マーケットカレンダー判定（営業日判定、next/prev trading day、SQ判定）や統計ユーティリティ

---

## セットアップ手順（開発環境向け）
以下は一般的なセットアップ手順の例です。プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください。

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install duckdb openai defusedxml

   注:
   - 実行時は urllib / 標準ライブラリも利用します。
   - 実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係をまとめてください。

3. リポジトリを編集可能インストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を作成すると自動で読み込まれます（settings モジュールで自動読込。無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
     - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime 等で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH            — データベースパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite パス（デフォルト data/monitoring.db）

サンプル `.env`（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な API / 実行例）
以下はライブラリの主要な関数を利用する簡単な例です。DuckDB 接続を作成して関数を呼び出します。

1. DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3. ニュースセンチメント（銘柄別 ai_scores）を生成
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4. 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5. 監査ログスキーマの初期化（監査用 DB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または in-memory:
# audit_conn = init_audit_db(":memory:")
```

6. マーケットカレンダー / 取引日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

7. ファクター計算 / リサーチ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# zscore 正規化例
normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
```

注意点:
- OpenAI 呼び出し部分はネットワーク/レート/エラー耐性を持つ実装ですが、APIキーや利用量には注意してください。
- LLM 呼び出しのテストでは、モジュール内の `_call_openai_api` をモックすることが想定されています。
- DuckDB の executemany に対する互換性配慮（空リスト禁止等）が実装で考慮されています。

---

## ディレクトリ構成（主なファイル）
リポジトリ内の主要なモジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数/設定読み込みユーティリティ
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースセンチメント算出（OpenAI 呼び出し）
    - regime_detector.py         # 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - etl.py                     # ETLResult 再エクスポート
    - news_collector.py          # RSS ニュース収集（SSRF 対策等）
    - calendar_management.py     # マーケットカレンダー管理 / 営業日ユーティリティ
    - quality.py                 # データ品質チェック
    - stats.py                   # 統計ユーティリティ（zscore_normalize）
    - audit.py                   # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         # Momentum / Value / Volatility 等
    - feature_exploration.py     # 将来リターン, IC, 統計サマリー 等
  - ai/、research/ などの他モジュール

---

## 運用上の注意 / ベストプラクティス
- 環境変数管理:
  - .env / .env.local を用いて API キー等を管理することができます。自動読み込みは config.py により実行されますが、テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます。
- Look-ahead バイアス防止:
  - 多くの処理（news window、regime 判定、ETL 等）で datetime.today() を直接参照しない設計になっています。バックテスト等で target_date を必ず指定してください。
- API レート制限・リトライ:
  - J-Quants や OpenAI の呼び出しはリトライ・バックオフ等を実装していますが、運用環境のレート制限やコストを考慮してください。
- DuckDB の互換性:
  - 一部処理では DuckDB の executemany の挙動に対する配慮（空リスト不可など）があります。DuckDB のバージョンに依存する差に注意してください。
- セキュリティ:
  - news_collector は SSRF・gzip bomb・XML 注入対策を実装していますが、追加のホワイトリストや運用上の検査を検討してください。

---

## 貢献 / 開発
- コードスタイル: ドキュメント内の設計方針に従い、安全・冗長性重視の実装（例: リトライ、入力バリデーション、フェイルセーフ）です。
- テスト: LLM 呼び出し等はモック可能な設計になっています（内部 _call_openai_api の差し替え等）。
- 追加実装例: 発注実行モジュール（kabuステーションとの連携）、バックテストフロー、Slack 通知ラッパー等を追加すると実運用に近づきます。

---

README の内容で不足している点や、特定のユースケース（例: CI での ETL 自動化、発注ワークフロー統合、ローカルでのデバッグ手順など）について詳しく知りたい場合は、目的を教えてください。必要に応じてサンプルスクリプトや推奨設定ファイルを追加します。