# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（参考実装）

このリポジトリは、日本株のデータ収集（J-Quants）→ 品質チェック → 特徴量作成 → AI によるニュース・センチメント評価 → 市場レジーム判定 → 監査ログ（注文追跡）といったワークフローを想定した内部ライブラリ群をまとめたものです。バックテストや自動化ジョブの基盤として利用できる設計方針・実装例を含みます。

主な設計方針（抜粋）
- ルックアヘッドバイアス防止（内部で date.today() を安易に使わず、明示的に target_date を渡す）
- DuckDB を中心としたローカルデータベース運用（冪等保存、トランザクション制御）
- 外部 API 呼び出しは再試行・バックオフやフェイルセーフを実装
- OpenAI（gpt-4o-mini）を使った JSON Mode による NLP スコアリング（JSON の厳密検証）
- セキュリティ対策（RSS の SSRF 防御、XML パースの安全化 等）

----

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）、必須変数チェック
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline: 日次 ETL（株価 / 財務 / カレンダー）と ETL 結果管理（ETLResult）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得と前処理（SSRF対策・gzipチェック・トラッキング除去）
  - calendar_management: 市場カレンダー管理（営業日判定・次/前営業日算出・更新ジョブ）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュース記事を銘柄ごとにまとめ、OpenAI へ投げてスコアを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の200日MA乖離とマクロニュースのLLMセンチメントを合成し market_regime に保存
- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ、ランク関数 等

（注）パッケージ __init__ で strategy / execution / monitoring といった上位レイヤを想定していますが、今回のコードベースでは主に data / ai / research 周りが実装されています。

----

## 依存関係（代表例）

実行に必要な代表的パッケージ（バージョン例は環境に合わせて調整してください）
- Python 3.10+
- duckdb
- openai
- defusedxml

pip でインストールする例:
```bash
pip install duckdb openai defusedxml
```

プロジェクトに requirements.txt がある場合はそれを使ってください（本スニペットは例示です）。

----

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成します。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード（自動売買 API 用）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必須）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知チャネルID
   - デフォルトで DuckDB / SQLite のパスは次のようになります（必要に応じて変更）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345...
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動ロードを無効にしたい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
     （テスト時等に利用）

5. データディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```

----

## 使い方（代表的な呼び出し例）

以下は Python REPL / スクリプトからの利用例です。各関数は明示的に DuckDB 接続や target_date を受け取る設計になっており、ルックアヘッドバイアスを避けるため日付は必ず呼び出し側で指定します。

- DuckDB 接続作成（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを含む）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（OpenAI を使って銘柄ごとの ai_scores を作成）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数 OPENAI_API_KEY を使用
print(f"scored {n} symbols")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化（監査専用 DuckDB を生成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は内部でスキーマ作成まで実行します
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意点（運用時）
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、APIキーや料金設定に注意してください。
- J-Quants の API レート制限（例: 120 req/min）はモジュール内で保護されていますが、運用レートは設計に合わせて調整してください。
- ETL / AI モジュールはデータベースのスキーマやテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を前提としています。初期スキーマがない場合は事前に作成する必要があります（本リポジトリのスキーマ作成ユーティリティ等を用意してください）。

----

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要ファイル・ディレクトリの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / .env 自動読み込み / settings
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP スコアリング（score_news）
    - regime_detector.py          -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
    - etl.py                      -- ETLResult の再エクスポート
    - news_collector.py           -- RSS 収集・前処理
    - calendar_management.py      -- 市場カレンダー管理
    - quality.py                  -- データ品質チェック群
    - stats.py                    -- 汎用統計ユーティリティ
    - audit.py                    -- 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py          -- ファクター計算（momentum/value/vol）
    - feature_exploration.py      -- 将来リターン・IC・統計サマリ等
  - ai/, data/, research/ は上位の機能群を含み、実運用のワークフローから呼び出します。

（注）実際のプロジェクトでは tests、scripts、docs、pyproject.toml などの補助ファイルを追加することを推奨します。

----

## 動作ポリシー・設計メモ（要点）

- 全体的に「冪等」設計を心がけています：ETL の保存は ON CONFLICT DO UPDATE、監査ログも ORDER_REQUEST_ID を冪等キーにする等。
- 外部 API 呼び出し時は再試行（指数バックオフ）やステータスコードに応じた振る舞い（401 → トークンリフレッシュ、429 → Retry-After 利用）を実装。
- ニュース収集では SSRF / XML Bomb / 大容量レスポンス対策を行っています（URL正規化、ホストのプライベート判定、defusedxml、サイズ上限）。
- AI スコアリングは JSON Mode を使い厳密にパース・バリデーションしており、レスポンスの不整合は安全側（スコア 0.0 やスキップ）へフォールバックします。
- バックテストや研究では「target_date を明示的に渡す」ことを守ることで未来情報の漏洩を防ぎます。

----

## 参考・トラブルシューティング

- 環境変数が未設定で ValueError が出る場合は `.env` を作成して必要な変数を設定してください。settings.* のプロパティは必須変数をチェックします。
- DuckDB にテーブルが存在しない場合、ETL・保存関数は空の結果を返すことがあります。スキーマ初期化が必要な場合は別途スキーマ定義スクリプトを用意してください。
- OpenAI の呼び出し時に rate limit や API エラーが出る場合はログでリトライの動作を確認し、APIキーやモデルの使用制限を確認してください。

----

この README はコードベースから読み取れる責務・インターフェースをまとめたものです。実運用にあたってはテーブルスキーマの初期化スクリプト、監視ジョブ、ログ収集・ローテーション、CI / CD の設定等を併せて整備することを推奨します。必要であれば、README に追記するサンプルスクリプトや schema.sql のテンプレートも作成できます。必要なら指示してください。