# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはリポジトリのコードから実装内容を推測して作成した初期リリース向けの変更履歴です。

※ バージョン番号はパッケージ定義 (kabusys.__version__ = "0.1.0") に合わせています。

## [Unreleased]

- ドキュメントやテスト用の小さな改善・追加を予定
- 将来的な互換性注意点や API 変更の追記予定

---

## [0.1.0] - 2026-03-27

### Added
- パッケージ初版として以下のモジュール群を追加。
  - kabusys.config
    - .env ファイルや環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント扱いのルール）。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - OS 環境変数を保護する protected 機能（.env.local を上書き可能だが OS 環境は保護）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム環境などをプロパティ経由で取得。
    - 必須環境変数未設定時は明示的に ValueError を送出するバリデーションを実装。

  - kabusys.ai.news_nlp
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）によりセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST の記事を対象）と chunk/batch 処理（最大20銘柄/チャンク）を実装。
    - 1銘柄あたりの記事数・文字数制限（トリミング）を実装してトークン肥大化を抑制。
    - レート制限・ネットワーク断・タイムアウト・5xx の場合に指数バックオフでリトライ。非再試行エラーはスキップして処理を継続（フェイルセーフ）。
    - OpenAI レスポンスの厳格なバリデーション（JSON パース、results 配列、code と score の型チェック、score の数値/有限性検査）と ±1.0 クリップ。
    - DuckDB との冪等書き込み（DELETE → INSERT、executemany の空配列対応の注意喚起）を実装。
    - テスト容易性のために内部の OpenAI 呼び出し関数を差し替えられる設計を採用。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組合せて日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存する機能を実装。
    - マクロニュースは news_nlp 側で定義されたウィンドウに基づき取得し、マクロキーワードでフィルタ。
    - OpenAI 呼び出しは独立実装・再試行ロジックを持ち、API失敗時は macro_sentiment=0.0 を採用するフェイルセーフを実装。
    - DB 操作は BEGIN/DELETE/INSERT/COMMIT のトランザクションで冪等に書き込み。失敗時は ROLLBACK を試行し例外を上位へ伝播。

  - kabusys.data.calendar_management
    - JPX カレンダー管理機能を提供。market_calendar を元に営業日判定・次営業日/前営業日取得・期間内営業日取得・SQ判定を実装。
    - market_calendar が未取得の際は曜日（土日）ベースのフォールバックを行う一貫したロジックを実装。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存の一連処理）。
    - 最大探索日数やバックフィル・先読み日数等の安全パラメータを導入して無限ループや過度な将来日付を防止。

  - kabusys.data.pipeline / kabusys.data.etl
    - ETL パイプラインの骨組みを実装。差分取得・保存・品質チェック（quality モジュールとの連携）を想定。
    - ETLResult データクラスを実装して取得件数・保存件数・品質問題・エラーを集約。to_dict により監査ログ用の辞書化をサポート。
    - jquants_client, quality と連携する設計。初回ロード用の最小日付やバックフィル、カレンダー先読み等のデフォルト設定を実装。

  - kabusys.research
    - factor_research: Momentum / Value / Volatility / Liquidity 等の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
      - calc_momentum: 1M/3M/6M リターン・200 日 MA乖離（データ不足時の挙動をロギング）。
      - calc_volatility: 20日 ATR・相対 ATR・20日平均売買代金・出来高比率。
      - calc_value: PER（EPS が存在かつ非ゼロ時）、ROE（raw_financials からの取得）。
    - feature_exploration: 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic：Spearman ランク相関）、factor_summary（count/mean/std/min/max/median）や rank ユーティリティを実装。
    - kabusys.data.stats の zscore_normalize を再エクスポートし、研究ワークフローへの統合を想定。

  - その他
    - パッケージの __init__ を設定し、主要サブモジュールを __all__ で公開。

### Changed
- 初版リリースにつき過去バージョンからの変更は無し（新規実装）。

### Fixed
- 初版リリースにつき過去バージョンからの修正は無し（新規実装）。
- 実装上の堅牢性向上点（レスポンスパース失敗時に外側の {} を抽出して復元する等）は実際の処理ロジックに組み込み済み。

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を送出して明示的に処理を中断する安全設計。
- .env 自動ロード時は OS 環境変数を protected として上書きを防止。

### Notes / Known limitations
- OpenAI（gpt-4o-mini）や J-Quants 等の外部 API に依存するため、これらの接続・認証情報の準備が必要。
- DuckDB のバージョン差に起因する executemany の空リスト制約等の互換性ワークアラウンドを実装している（注意：DuckDB のバージョン差異に注意）。
- タイムゾーンは UTC naive datetime を内部で使用（news ウィンドウは JST→UTC 変換済み）。全ての日付処理で lookahead バイアスを避けるために datetime.today()/date.today() を直接参照しない設計を採用している箇所がある（ただし calendar_update_job では実行日の date.today() を使用）。
- 本リリースは初期機能セットの提供に専念しており、将来的に API 仕様変更や性能改善（キャッシュ、並列化、より高度なリトライ戦略等）を予定。

---

この CHANGELOG はコード内容に基づく推測で作成しています。実際のリリースノートやユーザ向けドキュメントは、今後の変更や追加要件に合わせて更新してください。