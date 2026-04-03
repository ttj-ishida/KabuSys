# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
ETL・データ品質チェック・ニュース収集・LLM を使ったニュースセンチメント評価・市場レジーム判定・ファクター算出・監査ログ管理など、バックテスト・研究・運用に必要な基礎機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株に特化したデータプラットフォームと研究 / 運用ユーティリティ群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータ永続化（raw_prices, raw_financials, market_calendar 等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と NLP による銘柄毎・マクロセンチメントの算出（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化

設計上の特徴:
- ルックアヘッドバイアス対策（日時参照の扱いに注意）
- DuckDB を主なデータストアとして想定
- 冪等性（ETL / 保存処理は ON CONFLICT で上書き）
- フェイルセーフ（外部 API 失敗時もシステム全体が停止しない挙動）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local 自動ロード（無効化可）
  - 必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を取得する Settings クラス

- Data（kabusys.data）
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証 / レート制御 / リトライ）
  - pipeline: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）と ETLResult
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - calendar_management: 市場カレンダー判定・更新ジョブ
  - news_collector: RSS 収集（SSRF 対策、正規化、前処理、冪等保存準備）
  - audit: 監査ログ用スキーマ初期化（監査用テーブル / インデックス定義）
  - stats: z-score 正規化等の統計ユーティリティ

- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存

- Research（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats の再利用可能ユーティリティ

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.9+ またはプロジェクトの pyproject.toml に従う）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 最小（主要依存のみ）:
     - pip install duckdb openai defusedxml
   - パッケージ配布が用意されている場合:
     - pip install -e .    # プロジェクトルートに pyproject.toml / setup がある想定
   - テスト環境や追加ツールがあればそれらもインストールしてください。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動ロードされます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
     - OPENAI_API_KEY (AI 機能利用時 必須) — OpenAI API キー
     - KABUSYS_ENV (development | paper_trading | live) — 実行環境
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB など: data/monitoring.db）
     - その他（LINE 関連）: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - 必須環境変数が未設定の場合、Settings の該当プロパティが ValueError を投げます。
   - .env のフォーマットは一般的な KEY=VALUE をサポート。コメント / export 形式にも対応します。

---

## 使い方（主要なサンプル）

以下は対話的に利用する簡単な例です。適切に環境変数をセットした上で実行してください。

- DuckDB 接続と Settings の利用例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（全体パイプライン）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日が使われます
print(result.to_dict())
```

- 個別 ETL（株価のみ）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュースのセンチメント評価（OpenAI キー必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# score_news は ai_scores テーブルへ書き込むので、事前に conn を用意してください
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジームスコア算出（OpenAI キー必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / 研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

moms = calc_momentum(conn, date(2026, 3, 20))
fwd = calc_forward_returns(conn, date(2026, 3, 20))
ic = calc_ic(moms, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 監査ログ（audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作って監査テーブルを初期化して接続を受け取る
audit_conn = init_audit_db("data/audit.duckdb")
```

- 市場カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

is_td = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
```

注意:
- AI 関連の関数は OpenAI の API を呼び出します（API コスト・レート制限に注意）。
- jquants_client は J-Quants API のトークンを利用します（settings.jquants_refresh_token 必須）。

---

## ディレクトリ構成

プロジェクトの主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news 等）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                        — ETL インターフェース再エクスポート
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py             — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py        — 市場カレンダー管理 / 更新ジョブ
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - monitoring/ (存在を示唆するが実実装は別ファイル群になる想定)
  - execution/ (発注・実行関連は別モジュール想定)

（実際のリポジトリルートに pyproject.toml / .git / README.md 等がある想定）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（settings.kabu_api_password）

AI 関連:
- OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector）

運用 / ロギング:
- KABUSYS_ENV — 開発モード: development / paper_trading / live
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 に設定すると .env 自動ロードを無効化

DB パス:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）

その他:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知連携用（任意）

---

## 注意事項 / ベストプラクティス

- 本ライブラリの AI 部分は外部 API を呼びます。実行ごとに API 利用料が発生するので、開発時は小さなデータセットやモックを使ってください（テストでは _call_openai_api をモックできます）。
- run_daily_etl 等は実運用前にステージング環境で十分に検証してください。特に ETL の保存先や audit スキーマは一度作成するとデータが蓄積されます。
- .env には機密情報が含まれるため、バージョン管理に含めないでください（.gitignore を利用）。
- live 環境で発注や実際のブローカー連携を追加する場合、必ず冪等性・監査・エラーハンドリングを確認してください。

---

## 開発 / 貢献

- コードスタイル、テスト、CI 設定はリポジトリに合わせてください。
- 外部 API（OpenAI / J-Quants / RSS ソース）を使う関数は、テスト時にモックを注入して外部呼び出しを切り離す設計になっています。

---

必要であれば、README に以下を追加できます:
- API リファレンス（各関数の引数・戻り値のサンプル）
- 実運用でのデプロイ手順（systemd / cron / コンテナ化）
- サンプル .env.example

どの追加情報が必要か教えてください。