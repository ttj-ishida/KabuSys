# CHANGELOG

すべての重要な変更は Keep a Changelog の形式で記載しています。  
このファイルはパッケージの最初のリリースに基づき、コードベースから推測して要約した変更点・機能一覧を日本語で記載しています。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを導入。バージョンは `0.1.0` に設定。
  - パッケージ公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサーは `export KEY=val` 形式、クォート内のバックスラッシュエスケープ、およびインラインコメント処理に対応。
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - 必須環境変数取得用 `_require()` と、アプリ設定を集約する `Settings` クラスを提供。
  - `Settings` にて以下の設定プロパティを提供（バリデーション付き）:
    - J-Quants / kabu ステーション / Slack の必須トークン/ID
    - DBパスのデフォルト（DuckDB: `data/kabusys.duckdb`, SQLite: `data/monitoring.db`）
    - 実行環境（KABUSYS_ENV: development/paper_trading/live）
    - ログレベルの検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し、センチメントを ai_scores テーブルへ書き込み。
    - 時間ウィンドウは JST ベースで前日 15:00 〜 当日 08:30（内部では UTC naive datetime を使用）。
    - 1 チャンクあたり最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - OpenAI 呼び出しは JSON モードを期待し、レスポンスのバリデーション（results キー、型チェック、既知コードのみ採用）を実施。
    - スコアは ±1.0 にクリップ。API の一時エラー(429/ネットワーク断/タイムアウト/5xx)は指数バックオフでリトライ。致命的でない場合はスキップして処理継続（フェイルセーフ）。
    - DuckDB の executemany の挙動に合わせ、DELETE → INSERT の手順で置換（部分失敗時に他コードの既存スコアを保護）。

  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF（コード 1321、日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース由来の LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window で算出されるウィンドウからマクロキーワードでフィルタされ、OpenAI（gpt-4o-mini）でスコアリング。
    - OpenAI 呼び出しはリトライ実装あり。API 失敗時は macro_sentiment=0.0 をフォールバックして継続。
    - 最終結果は market_regime テーブルへ冪等的（BEGIN/DELETE/INSERT/COMMIT）に書き込み。

  - テスト容易性のため、OpenAI 呼び出しを抽象化（内部 `_call_openai_api`）し、ユニットテストからモック可能。

- データ関連モジュール (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダー（market_calendar）を扱うヘルパー群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar がない場合は曜日（平日）によるフォールバックを提供し、DB 登録がある日付は DB 値を優先。
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得し、バックフィル（直近数日を再取得）・健全性チェック（過度な未来日を検出してスキップ）を行う。
  - ETL パイプライン (`pipeline.ETLResult`)
    - ETL 結果を表すデータクラス ETLResult を追加（取得数／保存数／品質問題／エラー情報を含む）。to_dict で品質問題をシリアライズ。
    - ETL の差分取得、バックフィル、保存（idempotent）、品質チェックの方針を実装するための基盤を整備（実装は jquants_client/quality と連携する想定）。
  - ETL 公開インターフェース (`etl`) で ETLResult を再エクスポート。

- リサーチ / ファクター解析 (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）、Liquidity（20 日平均売買代金・出来高比率）を DuckDB の prices_daily / raw_financials テーブルから計算する関数を提供。
    - データ不足時は None を返すなどの堅牢な取り扱い。
    - 計算は SQL を主に使用し、外部 API には依存しない。結果は (date, code) ベースの dict リストで返却。
  - 特徴量探索ユーティリティ (`feature_exploration`)
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト 1/5/21 営業日）でのfwdリターンを計算。
    - IC（Information Coefficient）計算（calc_ic）：ファクターと将来リターンのスピアマンランク相関を計算（有効レコードが少ない場合は None）。
    - ランク変換ユーティリティ（rank）やファクター統計サマリー（factor_summary）を提供。
    - pandas 等の外部依存を避け、標準ライブラリのみで実装。

### 変更 (Changed)
- 初回リリースのため該当なし（新規導入）。

### 修正 (Fixed)
- 初回リリースのため該当なし（新規導入）。

### 設計上の注意点・フェイルセーフ
- ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を直接参照せず、呼び出し元から target_date を与える設計。
- OpenAI/API 呼び出しは一時的な失敗をリトライし、最終的に失敗しても例外を投げずフォールバックする箇所（ニュース NLP、レジーム判定）を設けてシステム全体の頑健性を確保。
- DuckDB の executemany に関する互換性制約に配慮した実装（空リスト回避など）。
- テスト容易性のため、内部 API 呼び出し関数はモック差し替え可能な形で実装。

---

注: 本 CHANGELOG は提供されたソースコードからの推定に基づいて作成しています。実際のリリースノート作成時はコミットログ・PR 説明・設計ドキュメントを参照して追記・修正してください。