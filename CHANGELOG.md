# Changelog

すべての変更は Keep a Changelog の形式に従います。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境・設定管理 (`kabusys.config`)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索して行うため、CWD に依存しない。
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - 優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き可能）
  - .env パーサは次をサポート:
    - コメント行/空行の無視、`export KEY=val` 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無し値の行内コメント判定（直前が空白/タブの `#` をコメントとみなす）
  - 必須設定取得時に未設定なら ValueError を送出する `_require` を提供
  - Settings クラスで以下の設定プロパティを公開:
    - J-Quants / kabuステーション / Slack / データベースパス / 環境（development/paper_trading/live）/ログレベル（DEBUG/INFO/...）など
    - デフォルト: `KABUSYS_ENV=development`, `LOG_LEVEL=INFO`, DuckDB および SQLite のデフォルトパス

- ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へ送信して銘柄別センチメント（ai_score）を算出し `ai_scores` テーブルへ書き込むバッチ処理を実装。
  - 主な機能:
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を算出する `calc_news_window`
    - 1銘柄当たり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）によるトリム
    - バッチ処理（1 API コールあたり最大 20 銘柄）
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score の型検証、未知コードは無視）
    - スコアは ±1.0 にクリップ
    - DuckDB への書き込みは部分失敗時に既存スコアを守るため、取得済みコードのみ DELETE→INSERT（トランザクション）で置換
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api がモック可能）

- マーケットレジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定して `market_regime` テーブルへ冪等書き込みする機能を実装。
  - 主な仕様:
    - ma200_ratio の算出は target_date 未満のデータのみ使用（ルックアヘッド防止）
    - マクロニュースは `news_nlp.calc_news_window` で定義されるウィンドウからキーワードフィルタで抽出
    - LLM には gpt-4o-mini を使用し JSON レスポンスを期待
    - API 失敗時は macro_sentiment = 0.0 としてフェイルセーフ継続
    - リトライや 5xx ハンドリング、JSON パース失敗時のフォールバックを実装
    - 最終的なスコアは clip(-1,1) で正規化し、閾値によりラベル付け
    - データベース操作は BEGIN/DELETE/INSERT/COMMIT と ROLLBACK 保護

- データ・カレンダー管理 (`kabusys.data.calendar_management`)
  - JPX カレンダー（market_calendar）の夜間差分更新ジョブ `calendar_update_job` 実装
    - J-Quants クライアント経由で差分取得・冪等保存（save_market_calendar）
    - バックフィル（直近 _BACKFILL_DAYS を必ず再フェッチ）と健全性チェック（過度に将来の日付はスキップ）
  - 営業日判定 API 群を実装:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB で値が存在する場合は DB 値を優先、未登録日は曜日（平日）ベースでフォールバック
    - _MAX_SEARCH_DAYS により探索範囲を制限し無限ループを防止
    - date オブジェクトで一貫して扱う

- ETL パイプライン基盤 (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約・辞書化できる機能を提供
  - 差分更新、バックフィル、品質チェックの設計方針を反映（実装の骨組み）

- 研究用（Research）ユーティリティ (`kabusys.research`)
  - ファクター計算: `calc_momentum`, `calc_value`, `calc_volatility`
    - Momentum: 1M/3M/6M リターン、MA200 乖離（MA200 行数不足時は None）
    - Volatility: 20 日 ATR、相対 ATR、出来高・売買代金指標
    - Value: 最新財務データと株価から PER/ROE を計算
  - 特徴量探索: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
    - forward_returns は任意ホライズン（デフォルト [1,5,21]）に対応、ホライズンの妥当性チェックあり
    - calc_ic は Spearman ランク相関（ties は平均ランク）を算出
    - factor_summary は count/mean/std/min/max/median を返す
  - z スコア正規化ユーティリティを `kabusys.data.stats.zscore_normalize` から再エクスポート

- パッケージ API 整備
  - 各サブパッケージの __all__ を整備し、主要関数を公開

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- （特記事項なし。ただし OpenAI API キー等は Settings 経由で必須チェックを行い、.env 自動ロードは無効化可能）

---

注記・設計上の重要点（開発者向け）
- ルックアヘッドバイアス対策: すべての「日付基準」ロジックは内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える設計。
- DB 操作の冪等性・トランザクション: news_nlp/regime_detector/calendar_update_job/ETL の DB 書き込みは冪等性を考慮した DELETE→INSERT または ON CONFLICT 相当の処理を採用し、例外時は ROLLBACK を試行。
- OpenAI 呼び出しの堅牢性: JSON Mode を使った厳格なレスポンス期待、JSON パース時は余分テキストを除去して復元を試みる等の耐性を持つ。また 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライする。
- テスト容易性: OpenAI 呼び出しポイント（_call_openai_api）はモジュール毎に独立実装され、ユニットテスト時に patch して差し替え可能。
- デフォルト値・必須環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（関数呼び出し時に明示的な api_key 引数を渡すことも可能）
  - DuckDB デフォルト: data/kabusys.duckdb
  - SQLite デフォルト: data/monitoring.db

移行メモ
- なし（初回リリース）