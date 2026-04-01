# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。  

フォーマット:
- 変更はセクション (Added, Changed, Fixed, Security) に分類しています。
- 各リリースにはバージョンと日付を付与しています。

## [Unreleased]

（作業中の変更や次回リリース予定の項目をここに記載してください）

---

## [0.1.0] - 2026-04-01

初期公開リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主要な追加点・設計方針・フェイルセーフ挙動などを以下にまとめます。

### Added
- パッケージ全体
  - パッケージメタ情報と公開インターフェースを追加（kabusys.__version__ = "0.1.0", __all__ 宣言）。
- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準）。これにより CWD に依存しない自動ロードを実現。
  - .env のパース実装（コメント・export 形式・シングル/ダブルクォート・バックスラッシュエスケープ対応）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを提供（J-Quants トークン、kabuステーション API、Slack 設定、DB パス、監視閾値、実行環境判定等）。
  - 必須環境変数未設定時は _require が ValueError を送出。
- AI 関連（kabusys.ai）
  - ニュースセンチメント解析（news_nlp.score_news）
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウ計算（UTC naive datetime）を実装。
    - raw_news と news_symbols を銘柄別に集約して OpenAI（gpt-4o-mini, JSON Mode）でバッチ評価。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数と文字数のトリム上限を採用（トークン肥大化対策）。
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。その他エラーはスキップして継続するフェイルセーフ設計。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー・型検証、未知コードの無視、数値チェック）とスコア ±1.0 のクリップ。
    - 成功した銘柄のみ ai_scores テーブルに置換（DELETE → INSERT）して部分失敗時でも既存スコアを保護。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - LLM（OpenAI gpt-4o-mini）呼び出しは専用実装で、API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - DuckDB を用いたルックアヘッドバイアス回避（target_date 未満のデータのみ参照）と、計算結果の冪等的書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブル優先の判定ロジック、未登録日は曜日ベースのフォールバック（土日非営業日）で一貫性を担保。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（バックフィル、先読み、健全性チェック実装）。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを追加（取得件数、保存件数、品質チェック結果、エラー一覧を含む）。
    - pipeline モジュールの骨子（差分更新、保存、品質チェック方針を反映）。
    - etl から ETLResult を再エクスポート。
- Research（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR、ATR比率）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の SQL/ウィンドウ関数で実装。
    - データ不足時の None 戻しや、計算対象の限定（prices_daily / raw_financials のみ）による安全設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（複数ホライズン対応、horizons の検証）、IC（Spearman ランク相関）計算、ランク関数（同順位は平均ランク）、ファクター統計サマリーを実装。
    - 外部依存を持たず標準ライブラリと DuckDB で完結する設計。

### Changed
- 一連の設計方針を明文化
  - ルックアヘッドバイアス回避のため、いかなる処理も datetime.today() / date.today() を内部参照しない設計（target_date を明示的に受け取る）。
  - OpenAI 呼び出しに対するリトライ戦略・パース失敗時のフェイルセーフを統一的に採用。
  - DB 書き込みはできるだけ部分的に置換することで、部分失敗時に既存データを保護する方針を全体で採用（ai_scores, market_regime 等）。
- 環境変数ローディングの優先順位と保護（protected keys）を導入し、OS 環境変数を意図せず上書きしないように実装。

### Fixed
- 不安定なバインドを回避するため、DuckDB 互換性を考慮して executemany による個別 DELETE を採用（配列バインド回避）。
- OpenAI レスポンスの JSON mode でも前後に余計なテキストが混在する場合があるため、最外の {} を抽出して復元する耐性を追加。
- market_calendar が存在しない場合でも、営業日判定が一貫して動作するように曜日フォールバックを整備。

### Security
- API キーの取り扱い
  - OpenAI API キーの解決は引数優先、その後環境変数 OPENAI_API_KEY を参照。未指定時は明示的に ValueError を発生させる（誤使用を防止）。
  - .env の自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

脚注・実装上の注意
- 多くのモジュールで DuckDB を前提とした SQL 実装を採用しています。テスト時は DuckDB の接続モックやユニットテスト用の小さな DB を使ってください。
- OpenAI 呼び出し部分はテスト容易性を考慮し、内部で _call_openai_api を分離しており unittest.mock.patch により差し替え可能です。
- ログメッセージは詳細な診断情報を含むよう設計しています。運用時はログレベルを調整して運用してください。

---

作成: kabusys チーム (自動生成ドキュメント)