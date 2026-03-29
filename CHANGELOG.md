# CHANGELOG

全ての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
日付はこのリリースを作成した日付です。

## [Unreleased]

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な機能、設計方針、および実装上の留意点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。主要サブパッケージを __all__ でエクスポート（data, research, ai, ...）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよびOS環境変数からの設定読み込みを自動化。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を基準）し、CWD に依存しない読み込みを実現。
  - .env のパースを堅牢化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い）。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数は保護され上書きされない）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - 必須環境変数チェック（_require）と Settings クラスを提供。J-Quants / kabuAPI / Slack / データベースパス / 環境（development/paper_trading/live） / ログレベルの検証や補助プロパティ（is_live, is_paper, is_dev）を実装。

- AI（自然言語処理）関連（kabusys.ai）
  - ニュースセンチメント分析（news_nlp.score_news）
    - raw_news と news_symbols を用いて銘柄単位に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数・文字数制限、429/ネットワーク/タイムアウト/5xx のエクスポネンシャルバックオフによるリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code と score の検証）、スコアの ±1.0 クリッピング。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）。部分失敗時に他の既存スコアを保護する実装。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（内部 _call_openai_api を patch 可能）。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによるニュースフィルタリング、LLM の結果は JSON で取得してパース。API 障害時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しのリトライ（429/接続/タイムアウト/5xx）や指数バックオフを実装。テスト時の差し替えを想定。

  - 共通設計方針
    - datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを防止。
    - OpenAI API 利用時に JSON mode を活用しつつ、JSON パース失敗に対する回復処理を実装（最外側の {} を抽出して復元を試行）。

- データ処理（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルに基づく営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースでフォールバック（週末は非営業日）。DB が部分的にしか無い場合でも一貫性を保つロジック。
    - calendar_update_job を実装し、J-Quants クライアントからの差分取得・バックフィル・保存を行う（健全性チェック、バックフィル日数、lookahead 設定）。
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質検査結果・エラー情報を集約）。
    - 差分取得、backfill、品質チェック（quality モジュール）を想定した ETL 設計（idempotent 保存、部分失敗の保護）。
    - jquants_client との連携を想定した差分・保存ロジックを含む。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を元に計算するユーティリティを実装。
    - データ不足時には None を返す設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズンをサポート）、IC（Spearman の ρ）計算、ランク付け（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を持たず、標準ライブラリと DuckDB SQL で完結。

### Changed
- 実装方針の明確化
  - 外部 API の障害に対しては例外を上位に伝播させずにフェイルセーフ（スコアを 0.0 にする、処理スキップなど）で継続する設計を採用。これによりバッチ処理全体の頓挫を防ぐようにしている。
  - DuckDB の互換性に配慮した実装（executemany に空リストを渡さない等の対策）。

### Fixed
- レスポンスパースの堅牢性向上
  - OpenAI の JSON モードでも稀に前後に余計なテキストが混ざるケースを想定し、最外の波括弧 {} を抽出して JSON を再解析するフォールバックを追加。
  - LLM が整数で code を返す等のバリエーションを受け入れるため、code を文字列で正規化して照合するように修正。
- DB トランザクション失敗時の対処
  - INSERT/DELETE 後の例外発生時に ROLLBACK を試行し、それでも失敗した場合はログを残す実装を追加（例外は上位へ伝播）。

### Security
- API キーの必須チェック（OpenAI / Slack / Kabu API / J-Quants）を導入し、未設定時は ValueError を送出して明確に失敗するようにした。

### Documentation / Tests（設計含む）
- 各モジュールに処理フロー・設計方針をモジュールドックストリングとして詳細に記載。ユニットテスト向けの差し替えポイント（_call_openai_api など）も明記しているためテスト容易性を確保。

---

注意:
- 本 CHANGELOG は現行ソースコードから推測して作成した初期リリースの変更履歴です。将来的なリリースでは、実運用中に検出された詳細なバグ修正・機能強化・互換性変更を個別に記載してください。