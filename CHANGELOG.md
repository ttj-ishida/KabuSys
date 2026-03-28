CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

バージョンルール: 0.1.0 が本リポジトリでの初回リリース相当のリリースです。

リンク: （リリースノートや差分リンクがあればここに）

Unreleased
----------

（今後の変更をここに記載）

0.1.0 - 2026-03-28
-----------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にてパッケージ名と公開モジュールの定義を追加。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルおよびOS環境変数からの設定読み込みを自動化。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検索して決定（CWD に依存しない）。
    - .env ファイルの行パースを実装（コメント行、export プレフィックス、クォート及びエスケープ対応、インラインコメント処理を含む）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）を環境変数から取得。未設定の必須変数は明示的なエラーを投げる。

- ニュース・NLP（AI）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - JST 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ化（最大 _BATCH_SIZE=20 銘柄/リクエスト）、1銘柄あたりの記事・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を導入。
    - JSON Mode を用いたレスポンス検証と堅牢なパース処理（余分な前後文字列を含む場合の復元処理含む）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - スコアは ±1.0 にクリップ。取得したスコアを ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時に他コードの既存スコアを保護）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily と raw_news を用いたデータ取得、OpenAI 呼び出し（gpt-4o-mini）、重みづけ・クリップ・閾値処理を実装。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）、ルックアヘッドバイアス対策（target_date 未満のデータのみ使用）。

  - 共通設計方針（AI モジュール）
    - OpenAI クライアント呼び出し部はテストで差し替え可能（モジュール内の private 関数経由）。
    - API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- データ処理・Research 機能
  - src/kabusys/research/*
    - factor_research.py
      - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）等のファクター計算を実装。
      - DuckDB を用いた SQL ベース実装。結果は (date, code) をキーとする dict のリストで返す。
      - データ不足時の None 戻しや行数チェック等の堅牢な挙動。
    - feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - pandas 等に依存せず標準ライブラリのみで実装。horizons のバリデーションや ties の平均ランク処理などを含む。
    - research パッケージの __all__ で主要関数をエクスポート。

- データ・プラットフォーム（Data）機能
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理: market_calendar テーブルを基に営業日判定・前後営業日検索・期間内営業日リスト取得・SQ判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時は曜日ベース（土日非営業日）でフォールバック。
    - next/prev_trading_day の最大探索範囲制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - 夜間バッチ更新 calendar_update_job を提供し、J-Quants API から差分取得・バックフィル・健全性チェック・冪等保存を行う。
    - jquants_client（外部モジュール）を経由した fetch/save 呼び出しに対応。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインに関するユーティリティを実装（差分取得、保存、品質チェックの統合設計）。
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors, has_errors 等）を実装して結果を構造化。
    - 最小データ開始日、デフォルトバックフィル日数、カレンダー先読み日数等の定数を定義。
    - テーブルの最大日付取得や存在チェックといった内部ユーティリティを提供。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開再エクスポート。

- その他
  - テストしやすさを意識した設計（OpenAI 呼び出し等をモック差し替え可能に実装）。
  - DuckDB を中心とした軽量な分析基盤設計。クエリは SQL で完結し、互換性考慮（DuckDB 0.10 など）を含む実装。

Changed
- （初回リリースのため過去バージョンからの変更はありません）

Fixed
- （初回リリースのため過去バージョンからの修正はありません）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- OpenAI API キーは引数または環境変数から明示的に渡す設計。機密情報の管理は Settings を通して行う想定（.env ファイルの取り扱いに注意）。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止のため、全ての日付関連処理は target_date ベースで過去データのみ参照する設計方針を一貫して適用。
- AI 呼び出しは失敗しても処理を継続するフェイルセーフを重視（多くのケースで macro_sentiment=0 やスコアスキップ）。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT戦略等）して部分失敗時のデータ保護を行う。
- DuckDB バインドや executemany の挙動（空リスト不可など）を考慮した実装が含まれる。

今後
- 監視・実行・発注関連のモジュール（execution / monitoring 等）の追加や、J-Quants / kabu クライアントの具体実装、テストカバレッジ拡充を予定。