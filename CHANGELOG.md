# CHANGELOG

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、語彙は日本語で記載しています。

全バージョンはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。
主な追加内容と設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージ定義とバージョン管理（__version__ = 0.1.0）。
  - パブリック API として data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）による .env ファイル探索を実装し、CWD に依存しない読み込みを実現。
  - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート／バックスラッシュエスケープに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードの無効化が可能。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB / システム設定などの読み取りプロパティ）。
  - 必須環境変数未設定時は明示的な ValueError を送出する _require を実装。
  - env (KABUSYS_ENV) と log_level (LOG_LEVEL) に対する入力検証を実装（許容値を限定）。

- データ層 (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装。
    - 差分更新、バックフィル、品質チェック（quality モジュール参照）の設計を反映。
    - ETLResult dataclass を定義し、実行結果の集約および to_dict 出力を提供。
    - DuckDB に対する存在チェックや最大日付取得ユーティリティを実装。
  - calendar_management モジュールを実装。
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティ。
    - market_calendar が未取得の場合の曜日ベースフォールバックや最大探索日数制限を設計。
    - J-Quants クライアント経由のフェッチ・保存処理との連携箇所を用意（jquants_client を参照）。

- 研究モジュール (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の算出。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率の算出。
    - calc_value: EPS ベースの PER と ROE の取得（raw_financials と組み合わせ）。
    - DuckDB 上の窓関数を利用した効率的な SQL ベース実装。
  - feature_exploration: 将来リターン、IC（Spearman）、ランク変換、統計サマリー等を実装。
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関を計算（有効レコードが3未満で None を返す）。
    - rank / factor_summary: ランク化（同順位は平均ランク）・基本統計量計算を標準ライブラリのみで実装。
  - re-export により主要関数をパッケージ外に露出。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む処理を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ計算（calc_news_window）。
    - 銘柄ごとに記事を集約し、1銘柄につき最大記事数・最大文字数でトリムしてプロンプト生成。
    - 1 API コールで最大 20 銘柄をバッチ処理（チャンク化）。
    - JSON mode を利用したレスポンス検証と堅牢なパース処理（余分な前後テキストの復元処理含む）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ付きリトライ、その他はスキップして継続するフェイルセーフ戦略。
    - DuckDB の executemany に関する空リスト注意（実行前に空チェック）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector: ETF (1321) の 200 日移動平均乖離とニュース由来のマクロセンチメントを組み合わせて日次市場レジーム判定（bull / neutral / bear）を実装。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - raw_news からマクロキーワードで記事抽出（最大 20 件）。
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）と堅牢なリトライ・フォールバック（API エラー時は macro_sentiment = 0.0）。
    - レジームスコア合成ロジック（MA 重み 70%、マクロ重み 30%）および market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に _call_openai_api を差し替え可能。

### 変更 (Changed)
- 設計上の注意点と方針を明確化
  - ルックアヘッドバイアス回避のため、AI/研究モジュールで datetime.today() / date.today() を直接参照しない方針を徹底（target_date を明示的に引数で受け取る）。
  - API 失敗時は例外を投げずにフェイルセーフ値（0.0 やスキップ）で継続する戦略を採用し、バッチ全体の停止を回避。
  - DB 書き込みはできる限り冪等に（削除→挿入や ON CONFLICT 相当）し、部分失敗時に既存データを保護する設計。

### 修正/改善 (Fixed / Improved)
- 環境変数パーサーの堅牢化
  - export プレフィックス、クォート付き値中のバックスラッシュエスケープ、インラインコメント処理、キー未設定行のスキップなどに対応。
  - .env.local を .env より優先して読み込むロジックを追加（OS 環境変数は保護）。

- OpenAI 連携の堅牢化
  - JSON mode を利用しつつ、JSON パース失敗時の救済処理（最外の {} を抽出して再パース）を実装。
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx をリトライ対象とし、非 5xx は即スキップする扱いを採用。
  - レスポンスのバリデーションルールを明示（必須キー・型チェック・未知コード無視・数値チェック・クリップ）。

- DuckDB 連携の堅牢化
  - テーブル存在チェック、最大日付取得ユーティリティを追加。
  - executemany に空リストを渡さないガードを実装（DuckDB 0.10 の制約対応）。

### 既知の制約 (Known issues / Notes)
- OpenAI API キーは必須（api_key 引数が None の場合は環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError を送出する。
- news_nlp/regime_detector は gpt-4o-mini を前提としたプロンプト設計と JSON mode を利用しているため、他モデルや将来の SDK 仕様変更には影響を受ける可能性がある（レスポンス構造や例外型の変化に対する互換性はある程度考慮済み）。
- calendar_update_job は jquants_client の実装に依存する（fetch/save のエラーは捕捉して 0 を返す設計）。
- 一部の機能は raw テーブル（prices_daily, raw_news, raw_financials, market_calendar, news_symbols, ai_scores 等）を前提としている。初期 DB スキーマ準備が必要。

### セキュリティ / 環境について (Security)
- OS 環境変数は .env による上書きから保護（読み込み時に既存 os.environ を protected として扱う）。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でオフ可能（CI・テスト用途）。

---

今後の予定（例）
- strategy / execution / monitoring の具体的なアルゴリズム実装と統合テスト。
- モデル切替やプロンプト最適化に伴うAI評価ロジックの改善。
- jquants_client の具体実装・API バージョン対応・テストカバレッジ拡充。

（この CHANGELOG はコードの実装から推測して作成しています。実際のリリースノートは用途に応じて調整してください。）