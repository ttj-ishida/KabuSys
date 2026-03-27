# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB をデータストアに、J-Quants や OpenAI（LLM）、RSS などを組み合わせてデータ収集・品質管理・ニュース NLP・市場レジーム判定・ファクター計算・監査ログを提供します。

---

## 概要

KabuSys は以下の目的で設計された Python パッケージ群です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB 保存）
- RSS を用いたニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- ETF の移動平均乖離＋マクロセンチメントを合成した市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ）および特徴量解析ツール
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注〜約定までを追跡する監査（audit）テーブル定義と初期化ユーティリティ
- 環境変数管理（.env 自動読み込み、設定ラッパー）

設計上の注意点：
- ルックアヘッドバイアスを避けるため、内部関数は date や window を明示的に受け取る設計です（datetime.today() / date.today() を直接参照しない関数が多くあります）。
- OpenAI（LLM）や外部 API 呼び出しはリトライ・フェイルセーフの方針を持っています（API 失敗時はデフォルト動作で継続する設計箇所が多い）。

---

## 主な機能一覧

- 環境設定
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定を簡単に取得できる settings オブジェクト（kabusys.config）

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants からの日次株価・財務・カレンダー取得（ページネーション対応）
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
  - 日次 ETL 実行エントリ（run_daily_etl）と個別 ETL

- ニュース収集 / 前処理（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news への保存と銘柄紐付け

- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄別ニュースを LLM へバッチ送信し ai_scores テーブルへ書き込み
  - JSON Mode のレスポンス検証とスコアクリッピング
  - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST 相当

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成
  - LLM によるマクロセンチメント評価（記事がある場合のみ呼ぶ）

- リサーチ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、将来日付 / 非営業日の検出
  - 各チェックは QualityIssue のリストを返す（停止せず問題を収集）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions とインデックスの定義
  - init_audit_db / init_audit_schema による初期化ユーティリティ

---

## セットアップ手順

前提：
- Python 3.9+（型アノテーションの union 記法などを使用）
- ネットワーク接続（J-Quants, OpenAI, RSS など外部 API へアクセスする場合）

1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージのインストール（例）
   実プロジェクトでは requirements.txt を用意してください。最低限必要なパッケージ例：
   ```bash
   pip install duckdb openai defusedxml
   ```
   (他に標準ライブラリのみで動くように設計されていますが、実行時に追加パッケージが必要な箇所があれば追記してください)

3. パッケージのインストール（ローカル開発）
   プロジェクトルートに setup.py / pyproject.toml がある場合は次を利用できます：
   ```bash
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは package import 時に行われます）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しで明示的に利用する場合（各関数は api_key 引数を受け取ります）
   - KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (任意): DEBUG / INFO / WARNING / ERROR / CRITICAL
   - DUCKDB_PATH / SQLITE_PATH (任意): データベースファイルパス（デフォルト data/kabusys.duckdb 等）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な例）

以下は主要な機能を呼び出す最小例です。実運用では適切な例外処理・ログ設定を行ってください。

- DuckDB 接続を作成して ETL を実行する例：
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（対象日・OpenAI API キーを渡す）：
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定：
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB 初期化（専用 DB を作る）：
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ書き込みやクエリが可能
```

- 環境設定の参照：
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定なら ValueError
print(settings.duckdb_path)            # Path オブジェクト
```

注意点：
- LLM 呼び出しはコストとレート制限があります。大量バッチを行う際は注意してください。
- ETL / API 呼び出しはネットワークエラーやレート制限を考慮した実装（リトライ、バックオフ、トークン更新）が組み込まれていますが、運用監視を推奨します。
- テスト時に LLM 呼び出しをモックするための差し替えポイントが用意されています（内部関数を patch する設計）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）プロジェクトは src/kabusys パッケージ内に整理されています。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — 銘柄別ニュース NLP スコアリング
    - regime_detector.py                — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - calendar_management.py            — 市場カレンダー管理（営業日判定など）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py                 — J-Quants API クライアント & DuckDB 保存
    - news_collector.py                 — RSS 収集・前処理
    - quality.py                        — データ品質チェック
    - stats.py                          — z-score 正規化など統計ユーティリティ
    - audit.py                          — 監査ログ schema / 初期化
    - etl.py                            — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py                — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py            — 将来リターン / IC / 統計サマリー
  - monitoring/ (存在を __all__ に含めているが詳細は実装に依存)

各モジュールはドキュメント文字列と設計方針を含んでおり、主要な関数に対して引数説明・返り値・副作用が明記されています。

---

## 運用・開発上の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の API 呼び出しや J-Quants の呼び出しはそれぞれ冪等性やリトライ戦略を備えていますが、API キーやトークンの管理は慎重に行ってください。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになる箇所があるため、ETL 実装の一部は空チェックを行っています。DuckDB のバージョンは互換性のある最新を推奨します。
- テスト時は外部 API 呼び出しを mock し、LLM や HTTP を実際に叩かないようにしてください（モジュール内の呼び出し関数を差し替える想定があります）。

---

もし README に追加したい内容（例: CI 設定、実運用のワークフロー、より詳細な設定例、サンプル .env.example の内容など）があれば教えてください。README をその要望に合わせて拡張します。