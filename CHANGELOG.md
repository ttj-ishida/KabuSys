# Changelog

すべての変更は Keep a Changelog の形式に準拠し、慣例に従ってセマンティックバージョニングを使用します。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買／データ基盤・リサーチ・AI評価の各機能を含む基礎実装を追加。

### 追加 (Added)
- パッケージ基盤
  - `kabusys` パッケージを導入。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: `__version__ = "0.1.0"`。

- 環境設定・ロード
  - `kabusys.config` モジュールを追加。
    - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを `.git` または `pyproject.toml` で探索）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - `.env` パーサ `_parse_env_line` は `export KEY=val` 形式、クォート内のエスケープ、行末コメントの扱い等をサポート。
    - OS 環境変数を保護するための `protected` set を用いた上書き制御（`.env.local` は override=True）。
    - `Settings` クラスにより、必要な環境変数をプロパティで提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 等）。
    - 各種デフォルト（`KABUSYS_ENV`、`LOG_LEVEL`、`KABU_API_BASE_URL`、DB パスなど）とバリデーションを実装 (`env` と `log_level` の許容値チェック、`is_live`/`is_paper`/`is_dev` の便宜プロパティ)。

- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp` を追加。
    - `score_news(conn, target_date, api_key=None)` により raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄ごとのニュースセンチメント（ai_scores テーブルへ書き込み）を実装。
    - タイムウィンドウ計算 (`calc_news_window`) は JST 基準（前日 15:00 JST 〜 当日 08:30 JST）を UTC naive datetime に変換して扱う。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの記事数・文字数制限（`_MAX_ARTICLES_PER_STOCK`, `_MAX_CHARS_PER_STOCK`）を導入。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライし、その他エラーはスキップするフェイルセーフ設計。
    - レスポンス検証 (`_validate_and_extract`) により JSON 抽出、構造検証、数値変換、スコアの ±1 クリップを実施。
    - DB 書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）し、DuckDB の制約（executemany の空リスト不可）への対応あり。
    - テスト容易性のため `_call_openai_api` を直接差し替え可能（patch を想定）。
  - `kabusys.ai.regime_detector` を追加。
    - ETF 1321（国内日経連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - MA 計算はルックアヘッドバイアスを避けるため target_date 未満のデータのみを使用し、データ不足時は中立（ma200_ratio=1.0）にフォールバックして警告ログを出す。
    - マクロ記事の抽出はキーワードマッチで最大件数を制限（`_MAX_MACRO_ARTICLES`）。
    - LLM 呼び出しは `gpt-4o-mini` の JSON Mode を利用、API 障害時は macro_sentiment=0.0 とするフェイルセーフ、リトライと指数バックオフを実装。
    - 結果は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。

- データ基盤（Data）
  - `kabusys.data.pipeline` モジュールを追加。
    - ETL の設計思想（差分取得、バックフィル、品質チェック、idempotent 保存）に準拠した実装。`ETLResult` dataclass による実行結果の集約とシリアライズ (`to_dict`) を提供。
    - DuckDB 上のテーブル存在チェック、最大日付取得等のユーティリティを実装。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - `kabusys.data.calendar_management` を追加。
    - JPX カレンダー管理と営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - カレンダーの夜間差分取得ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装。J-Quants クライアントから差分を取得し、save 関数で冪等保存。バックフィル・健全性チェック（未来日過多の検出）を備える。
    - カレンダーデータが一部しかない場合でも DB 値を優先し、未登録日は曜日フォールバックで一貫性を保つ設計。

- リサーチ（Research）
  - `kabusys.research` 名前空間を導入。公開:
    - `calc_momentum`, `calc_value`, `calc_volatility`（`research.factor_research`）
    - `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`（`research.feature_exploration`）
    - `zscore_normalize` は `kabusys.data.stats` から再エクスポート（参照のみ・実装ファイルは別途想定）。
  - `research.factor_research`:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）を DuckDB の SQL/ウィンドウ関数で計算する関数群を実装。
    - データ不足時は None を返す振る舞いで、結果は (date, code) ベースの dict のリストとして返却。
  - `research.feature_exploration`:
    - 将来リターン計算（可変ホライズン）`calc_forward_returns` を実装。horizons の妥当性チェックあり。
    - IC（Spearman の ρ）を計算する `calc_ic`（欠損/定数分散ハンドリング）。
    - 基本統計量を算出する `factor_summary`、並び替えで順位を返す `rank` を実装（同順位は平均ランク）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 環境変数ロードにおいて OS の既存環境変数を保護する挙動を採用（`.env` による上書きはデフォルトで無効、`.env.local` は明示的に上書き可能だが OS 環境変数は protected）。  
- 必須の API キー（OpenAI 等）未設定時は明示的な ValueError を出して早期検出。

### 既知の設計上の注意点 / 制約
- DuckDB を前提としているため、executemany の空リストやリスト型バインドの挙動に対する互換性対策を実装している（空リストでの executemany を避けるガードなど）。
- OpenAI 呼び出しは JSON Mode を前提とするが、稀に前後に余分なテキストが含まれるケースに対して補完的に最外側の `{...}` を抽出してパースを試みる処理を実装している。
- 全ての「日付」ロジックはルックアヘッドバイアス防止のために target_date を引数で受け、内部で datetime.today()/date.today() を直接参照しない方針を採用している（再現性の高いバックテストに配慮）。
- API キーは `api_key` 引数で注入可能にしており、テストでの差し替えが容易になっている。LLM 呼び出しの内部関数はテスト用に patch しやすい形で設計。

### 互換性に関する注記 (Breaking Changes)
- 初回リリースのため Breaking Changes はありません。

---

以上がリリース 0.1.0 相当の変更点の要約です。実装の詳細や追加の履歴を反映する場合は、該当モジュールの更新時にバージョンとセクションを追記してください。