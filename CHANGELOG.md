# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠します。  
このファイルにはパッケージの主要な追加機能、変更点、修正点、及び重要な設計上の決定を記載しています。

注: バージョン番号はパッケージ内の `src/kabusys/__init__.py` の `__version__`（0.1.0）に合わせています。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（`src/kabusys/__init__.py`）。公開モジュール群として `data`, `strategy`, `execution`, `monitoring` を公開。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイル / 環境変数の自動読み込み機能を実装。プロジェクトルート検出は `.git` または `pyproject.toml` を探索して行うため、CWD に依存しない設計。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーで以下をサポート:
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無し時のインラインコメント（`#`）取り扱い（直前が空白/タブのときのみコメント判定）
  - `.env` と `.env.local` の読み込み順序と上書きポリシー（OS 環境変数の保護）を実装。
  - 必須環境変数チェック用 `_require` と `Settings` クラスを提供。主要プロパティ:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB, SQLite） / システム設定（KABUSYS_ENV, LOG_LEVEL）
  - `KABUSYS_ENV` と `LOG_LEVEL` の入力検証（許容値チェック）を実装。`is_live` / `is_paper` / `is_dev` の利便性プロパティを提供。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを取得し `ai_scores` テーブルへ書き込む `score_news` を実装。
    - タイムウィンドウ（JST: 前日 15:00 〜 当日 08:30）を UTC naive datetime に変換する `calc_news_window` を実装。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事文字数上限、記事数上限を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API 応答の厳格なバリデーション（JSON 抽出、`results` 配列、code/score 検証）を実装。
    - スコアは ±1.0 にクリップ。部分成功時の DB 置換ロジック（対象コードのみ DELETE → INSERT）で既存データ保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に実装（内部の `_call_openai_api` は monkeypatchable）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム (`bull` / `neutral` / `bear`) を判定する `score_regime` を実装。
    - MA200 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロキーワードで raw_news をフィルタして最大 20 件のタイトルを LLM に提供。LLM 呼び出し失敗時はフォールバックで macro_sentiment = 0.0。
    - API 呼び出しのリトライ（指数バックオフ）・エラー分類・JSON パースの堅牢化を実装。
    - 判定結果は `market_regime` テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム (`kabusys.data`)
  - マーケットカレンダー管理 (`data.calendar_management`)
    - JPX カレンダーの夜間差分取得ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル・健全性チェックを含む）。
    - 営業日判定・前後営業日探索・期間内営業日列挙・SQ 日判定のユーティリティを実装:
      - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - カレンダーデータがない場合は曜日（平日）ベースでフォールバックする一貫した挙動を設計。
    - 最大探索日数 `_MAX_SEARCH_DAYS` による無限ループ防止、バックフィル `_BACKFILL_DAYS`、先読み `_CALENDAR_LOOKAHEAD_DAYS`、健全性閾値 `_SANITY_MAX_FUTURE_DAYS` の導入。
  - ETL パイプライン (`data.pipeline`, `data.etl`)
    - ETL 実行結果を整理する `ETLResult` データクラスを公開（`data.etl` で再エクスポート）。
    - 差分取得のためのユーティリティ（テーブル存在確認、最大日付取得）を実装。
    - ETL の設計方針として差分更新、バックフィル、品質チェックの収集（Fail-Fast しない）を反映。

- リサーチ / ファクター (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を計算する `calc_momentum`, `calc_value`, `calc_volatility` を実装。
    - 各関数は DuckDB 接続を受け取り、必要テーブル（`prices_daily`, `raw_financials`）のみ参照。外部 API へのアクセスは行わない設計。
    - データ不足時の振る舞い（例: MA200 行数不足時は None を返す）を定義。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、ホライズン検証あり）
    - IC（Information Coefficient）計算 `calc_ic`（Spearman ランク相関）
    - 値をランク変換する `rank`（同順位は平均ランク）
    - ファクター統計サマリー `factor_summary`
  - `kabusys.research.__init__` により主要関数をパッケージ公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI / kabu API / Slack などの機密情報は環境変数経由で必須設定にし、未設定時は明確な例外を投げる設計（`_require` / `Settings`）。
- .env の自動読み込み時、既存の OS 環境変数を保護するために保護セット（protected）を導入。`.env.local` は上書き可能だが OS 環境は上書きされない。

### Notes / Design decisions
- ルックアヘッドバイアス対策:
  - AI スコアリング・レジーム判定・ファクター計算・将来リターン計算等は内部で `datetime.today()` / `date.today()` を参照しない（すべて `target_date` を明示的に受け取る）。
  - DB クエリは target_date に対して排他的条件（`< target_date`）や適切なウィンドウを使用。
- OpenAI 呼び出しは冪等性や一時障害に強い実装（リトライ / バックオフ / フェイルセーフフォールバック）を採用。テスト時に差し替え可能な設計。
- DuckDB のバージョン差異（executemany の空リスト問題、配列バインドの不安定さ）を考慮した実装を行っている（個別 DELETE の executemany など）。

---

今後のリリースで想定される追加項目（例）
- 発注（execution）や運用監視（monitoring）モジュールの具体実装と E2E テスト。
- Strategy 関連のモデル化とバックテスト機能の公開。
- ドキュメント・例示的な ETL 実行手順・CI 用のテストセットアップの追加。