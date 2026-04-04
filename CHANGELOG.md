Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」に準拠し、SemVer（例: 0.1.0）を使用します。

Unreleased
----------

（次回リリースまでの変更をここに記載します）

[0.1.0] - 2026-04-04
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージのエントリポイントを定義（kabusys.__version__ = 0.1.0, __all__ に主要サブパッケージを公開）。
- 環境変数・設定管理（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント処理（クォート無しの場合の # 扱いの微妙な規則）。
  - .env/.env.local の読み込み優先度制御（OS環境変数の保護、override 制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化）。
  - Settings クラスを提供し、各種設定（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境モード）をプロパティ経由で取得可能に。
  - 必須変数未設定時は明確なエラーメッセージを投げる _require() 実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄単位に記事を統合し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを生成。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1銘柄あたりの最大記事数/文字数トリム、スコア ±1.0 クリップ。
    - JSON Mode レスポンスのバリデーション・復元ロジック（前後余分テキストが混ざった場合の {} 抽出）。
    - レート制限・接続断・タイムアウト・5xx に対する指数バックオフリトライ。
    - DuckDB への冪等書き込み（部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能な設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からのルックアヘッド防止クエリ、raw_news のキーワードフィルタリング、OpenAI（gpt-4o-mini）呼び出し、冪等な market_regime テーブル書込を実装。
    - API エラー発生時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - OpenAI 呼び出しのリトライ戦略（429/ネットワーク/タイムアウト/5xx）とログ出力。
- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装: J-Quants から差分取得→冪等保存（ON CONFLICT DO UPDATE）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得・不完全な場合の曜日ベースフォールバックと最大探索日数上限を導入（無限ループ防止）。
    - 健全性チェック（将来日付の異常検出）やバックフィル機能を備える。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - DataPlatform の差分取得/保存/品質チェックフローを実装するための骨組み。
    - ETLResult データクラスを実装・エクスポート（kabusys.data.ETLResult）。取得件数、保存件数、品質問題、エラー一覧などを集約可能。
    - テーブル存在確認、最大日付取得等のユーティリティを実装。
- リサーチ機能（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン & 200 日 MA 乖離の算出（営業日ベースのラグを利用）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の算出。
    - calc_value: raw_financials と prices_daily を組合せた PER, ROE の算出（EPS 不在や 0 の場合は None）。
    - 設計上、DuckDB 接続を受け取り外部 API にはアクセスしない点を明記。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（任意の営業日ホライズン）を一度のクエリで取得する実装。
    - calc_ic: Spearman ランク相関（IC）を計算する実装（欠損/非有限値の除外、最小有効レコード数チェック）。
    - rank, factor_summary: 同順位平均ランク付け、基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージ __all__ で主要関数を公開。
- 共通実装・品質
  - DuckDB を主なデータストアとして利用する実装パターンを採用（冪等保存、executemany の空リスト回避等の互換性考慮）。
  - ルックアヘッドバイアス回避方針を明確に採用（datetime.today()/date.today() を計算ロジックで直接参照しない箇所がある旨、また window クエリで排他条件を採用）。
  - ロギングと詳細な警告メッセージを多用し、失敗時は例外を上位に伝播する箇所とフェイルセーフで継続する箇所を明確に分離。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI / 外部 API キーは引数注入または環境変数（OPENAI_API_KEY）経由で解決。未設定時は明示的なエラーを発生させ、誤った公開を防止。

Notes / Implementation details
- OpenAI 呼び出しは各モジュールで独自にラップしており、テスト時に差し替えやすい構造（モジュール結合を避ける）。
- .env 読み込みの振る舞い（override / protected）により、CI/本番環境の OS 環境変数を安全に優先できる設計。
- DuckDB のバージョン差異へ配慮した実装（例: executemany に空リストを渡さない等）。

Acknowledgements / External dependencies
- OpenAI（gpt-4o-mini）を外部 LLM として利用する想定。
- J-Quants API をデータ元として利用するためのクライアント（kabusys.data.jquants_client）を参照・利用。

----------

バグ報告、改善提案、またはリリースノートの補足を希望される場合は変更点や目的（例: どの関数／ファイルに注目してほしいか）を教えてください。