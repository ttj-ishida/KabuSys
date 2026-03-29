# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。
リリースはセマンティックバージョニングに従います。

- リリースノートの書式: https://keepachangelog.com/ja/1.0.0/
- 最終更新日: 2026-03-29

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージ公開のためのトップレベル __all__ を定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - .env パーサ実装（export 形式、クォート処理、インラインコメントの扱い、保護付き上書き機能）。
  - 必須環境変数取得ヘルパ（_require）。検証付きプロパティ:
    - J-Quants / kabu / Slack / DB パス（duckdb/sqlite）/ 環境モード（development/paper_trading/live）/ログレベル等。
  - 不正な環境値に対する明確な ValueError を導入。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（JST ベース → UTC 変換）`calc_news_window` を提供。
    - バッチ処理（1回あたり最大 20 銘柄）、記事数/文字数トリム、JSON Mode を利用したレスポンス検証を実装。
    - 再試行（指数バックオフ）・5xx/タイムアウト/ネットワーク断に対するリトライポリシー、失敗時はログ出力してスキップするフェイルセーフを実装。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api の patch を想定）。
    - レスポンス検証ロジック（スキーマ検証・不正値除外・スコアクリップ）を実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロキーワードベースで raw_news をフィルタし、記事がある場合のみ LLM を呼ぶ（記事なければ macro_sentiment=0.0）。
    - LLM 呼び出しに対するリトライ（指数バックオフ）と失敗時の安全なフォールバックを実装。
    - ルックアヘッドバイアス防止の設計（datetime.today() を参照しない、DB クエリに排他条件を付与）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ユーティリティを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - JPX カレンダー差分取得の夜間バッチ（calendar_update_job）を実装（J-Quants クライアント経由）。
    - カレンダー更新時のバックフィル、健全性チェック、最大探索日数制限を実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を格納する dataclass `ETLResult` を追加（品質チェック結果・エラー集計・保存件数等を含む）。
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック統合のための設計に準拠したユーティリティを実装。
    - 内部ユーティリティ（テーブル存在チェック・最大日付取得・市場カレンダー補正）を追加。

- 研究用ツール群（kabusys.research）
  - `factor_research`（calc_momentum / calc_value / calc_volatility）
    - モメンタム、バリュー、ボラティリティ（ATR）等のファクターを DuckDB SQL を使って計算する関数を実装。
    - データ不足時の None ハンドリング、営業日ベースのホライズン設計。
  - `feature_exploration`（calc_forward_returns / calc_ic / factor_summary / rank）
    - 将来リターン計算、IC（スピアマン）計算、ランク変換、統計サマリーを提供。
    - pandas 等の外部依存を使わずに標準ライブラリと DuckDB で実装。

- その他
  - DuckDB を主要な分析 DB として採用。多くの処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で安全に書き込みを行う設計。
  - ロギングを各モジュールに導入し、運用時の可観測性を確保。
  - API キー無しの実行で発生する ValueError の明示化（OpenAI, Slack, J-Quants などの必須キー）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- .env 自動ロード時、既存 OS 環境変数は protected として上書きされないよう保護（意図しないシークレット上書きを防止）。
- 外部 API キー（OpenAI など）は環境変数からのみ取得可能で、未設定時は明示的なエラーメッセージを返す。

### Notes / Known limitations
- OpenAI（gpt-4o-mini）を利用する機能は API キー（OPENAI_API_KEY）を必要とします。テスト時は api_key 引数経由で注入可能。
- DuckDB のスキーマ（prices_daily, raw_news, market_regime, ai_scores, raw_financials, news_symbols, market_calendar など）を前提としています。スキーマ不備や未作成テーブルは関数で None や 0 を返す等のフォールバックが入りますが、適切なデータ準備が前提です。
- ニュース処理 / レジーム判定は LLM レスポンスの形式に依存します。JSON Mode を利用しているが、まれにパース不能なレスポンスが返る場合はスキップして進行します（フェイルセーフ）。
- ETL / カレンダー更新は jquants_client の実装に依存します（本コードでは jquants_client をインポートして使用）。
- 本バージョンでは実際の発注（kabu ステーション等）や監視（monitoring）コードの詳細は含まれていない（パッケージ構成上の名前空間は用意）。

### Migration / Usage tips
- .env.example を参考に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を設定してください。
- DuckDB のデフォルトパスは `data/kabusys.duckdb`、SQLite のデフォルトパスは `data/monitoring.db`。必要に応じて環境変数（DUCKDB_PATH, SQLITE_PATH）で変更可能です。
- 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- OpenAI 呼び出し箇所はユニットテストで patch できるように設計されています（例: unittest.mock.patch で _call_openai_api を差し替え）。

---

今後の予定（例）
- モニタリング / 実行（execution, monitoring）モジュールの実装・統合
- CI 上での DuckDB スキーマ準備用ユーティリティ追加
- ユニットテストの充実（LLM モック・DuckDB 用フィクスチャ等）
- パフォーマンス改善（大規模データ処理時のチャンク制御・並列化検討）